"""Small direct-HTTP Jev adapter. No third-party dependencies or text generation."""

import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def number(value, low=0, high=1):
    return (type(value) in (int, float) and math.isfinite(value)
            and low <= value <= high)


def validate_questions(questions):
    if not isinstance(questions, dict) or not questions:
        raise ValueError("questions must be a nonempty object")
    for key, question in questions.items():
        if not isinstance(key, str) or not key or not isinstance(question, dict):
            raise ValueError("invalid question entry")
        if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
            raise ValueError("each question needs explicit string instructions")
        kind, criteria = question.get("type"), question.get("criteria")
        if kind == "noul":
            if criteria is not None and (not isinstance(criteria, dict)
                    or set(criteria) != {"true", "false"}
                    or not all(isinstance(v, str) and v for v in criteria.values())):
                raise ValueError("Noul criteria must describe true and false")
        elif kind == "choice":
            if (not isinstance(criteria, dict) or not 2 <= len(criteria) <= 255
                    or not all(isinstance(k, str) and k and isinstance(v, str) and v
                               for k, v in criteria.items())):
                raise ValueError("Choice needs 2-255 named, described options")
        elif kind == "score":
            if (not isinstance(criteria, list) or not 2 <= len(criteria) <= 10
                    or not all(isinstance(v, str) and v for v in criteria)):
                raise ValueError("Score needs 2-10 descriptive levels")
        else:
            raise ValueError("unsupported question type")


def validate_response(response, questions):
    if not isinstance(response, dict) or not isinstance(response.get("model"), str):
        raise ValueError("response needs a model")
    answers = response.get("answers")
    if not isinstance(answers, dict) or set(answers) != set(questions):
        raise ValueError("response question IDs do not match")
    for key, question in questions.items():
        answer, kind = answers[key], question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError("answer type does not match question")
        if kind == "noul":
            if not number(answer.get("noul")):
                raise ValueError("invalid Noul probability")
            continue
        expected = (set(question["criteria"]) if kind == "choice"
                    else {str(i) for i in range(len(question["criteria"]))})
        probabilities = answer.get("probabilities")
        if (not isinstance(probabilities, dict) or set(probabilities) != expected
                or not all(number(p) for p in probabilities.values())
                or not math.isclose(sum(probabilities.values()), 1, abs_tol=0.001)
                or not number(answer.get("confidence"))):
            raise ValueError("invalid answer distribution")
        if kind == "choice":
            selected = answer.get("choice")
            if selected not in expected or probabilities[selected] < max(probabilities.values()):
                raise ValueError("invalid Choice winner")
        else:
            mean = sum(int(i) * p for i, p in probabilities.items())
            if (not number(answer.get("score"), 0, len(expected) - 1)
                    or not math.isclose(answer["score"], mean, abs_tol=0.01)
                    or answer.get("legend") != dict(enumerate_strings(question["criteria"]))):
                raise ValueError("invalid Score value or legend")
    return answers


def enumerate_strings(values):
    return ((str(i), value) for i, value in enumerate(values))


def noul(instructions):
    return {"type": "noul", "instructions": instructions}


def choice(instructions, criteria):
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions, criteria):
    return {"type": "score", "instructions": instructions, "criteria": criteria}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Jev:
    """Offline by default. Every decision refers back to a recorded request hash."""

    def __init__(self, *, live=False, model="jev-1.13.0", replay=None,
                 local_bytes=24000, request_bytes=48000, max_requests=1000,
                 yes=0.8, no=0.2, confidence=0.8, transport=None):
        if (not number(no) or not number(yes) or not no < 0.5 < yes
                or not number(confidence)):
            raise ValueError("thresholds require 0 <= no < 0.5 < yes <= 1")
        if (type(local_bytes) is not int or type(request_bytes) is not int
                or not 512 <= local_bytes <= 24000
                or not local_bytes <= request_bytes <= 48000
                or type(max_requests) is not int or max_requests < 1):
            raise ValueError("invalid request budgets")
        if live and replay is not None:
            raise ValueError("live and replay modes are mutually exclusive")
        self.live, self.model = live, model
        self.local_bytes, self.request_bytes = local_bytes, request_bytes
        self.max_requests = max_requests
        self.yes, self.no, self.confidence = yes, no, confidence
        self.records, self.attempts = [], 0
        self.replay = {r["request_id"]: r for r in (replay or {}).get("requests", [])}
        self.transport = transport or self._http
        self.key = os.environ.get("TYPESAFE_API_KEY", "") if live else ""
        if live and transport is None and not self.key:
            raise ValueError("TYPESAFE_API_KEY is required for --live; use offline mode otherwise")

    def _http(self, body):
        request = urllib.request.Request(
            "https://api.typesafe.ai/v1/systemone", data=encoded(body),
            headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        # Disable redirects so a key cannot be forwarded to another host.
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
            return json.load(response)

    def _fits(self, state, questions):
        return (len(encoded(state)) + max(len(encoded(q)) for q in questions.values()) + 512
                <= self.local_bytes and len(encoded({"model": self.model, "state": state,
                                                     "questions": questions})) <= self.request_bytes)

    def ask(self, state, questions):
        validate_questions(questions)
        # Split independent questions, never truncate the shared evidence.
        groups, group = [], {}
        for key, question in questions.items():
            candidate = {**group, key: question}
            if group and not self._fits(state, candidate):
                groups.append(group)
                group = {}
            group[key] = question
        if group:
            groups.append(group)
        decisions = {}
        for group in groups:
            body = {"model": self.model, "state": state, "questions": group}
            request_id = digest(body)
            record = {"request_id": request_id, "request": body, "status": "pending"}
            response = None
            if not self._fits(state, group):
                record["status"] = "oversized"
            elif request_id in self.replay:
                saved = self.replay[request_id]
                if digest(saved.get("request")) == request_id and saved.get("response"):
                    response = saved["response"]
                else:
                    record["status"] = "invalid_replay"
            elif self.live:
                for attempt in range(3):
                    if self.attempts >= self.max_requests:
                        record["status"] = "budget_exhausted"
                        break
                    self.attempts += 1
                    try:
                        response = self.transport(body)
                        break
                    except urllib.error.HTTPError as error:
                        record["status"] = "http_" + str(error.code)
                        if error.code not in (429, 500, 502, 503, 504, 529) or attempt == 2:
                            break
                        time.sleep(2 ** attempt)
                    except (OSError, ValueError):
                        record["status"] = "transport_error"
                        break
            answers = {}
            if response is not None:
                try:
                    answers = validate_response(response, group)
                    # Persist only expected fields; never arbitrary upstream error data.
                    record.update(status="evaluated", response={
                        "model": response["model"], "answers": answers,
                        "usage": response.get("usage", {})})
                except (ValueError, TypeError):
                    record["status"] = "invalid_response"
            self.records.append(record)
            for key, question in group.items():
                answer = answers.get(key)
                label = "unresolved"
                if answer:
                    if question["type"] == "noul":
                        label = ("yes" if answer["noul"] >= self.yes else
                                 "no" if answer["noul"] <= self.no else "unresolved")
                    elif answer["confidence"] >= self.confidence:
                        label = answer.get("choice", "evaluated")
                decisions[key] = {"request_id": request_id, "status": record["status"],
                                  "answer": answer, "label": label}
        return decisions

    def audit(self):
        return {"schema_version": 1, "model": self.model,
                "mode": "live" if self.live else "replay" if self.replay else "offline",
                "policy": {"yes": self.yes, "no": self.no, "confidence": self.confidence,
                           "local_bytes": self.local_bytes, "request_bytes": self.request_bytes,
                           "max_requests": self.max_requests},
                "attempts": self.attempts, "requests": self.records}

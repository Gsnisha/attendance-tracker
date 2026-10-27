import os
import sqlite3
from datetime import date

from flask import Flask, flash, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")
app.config["DATABASE"] = os.environ.get("DATABASE", "/tmp/attendance.db")

STATUSES = ("Present", "Late", "Absent")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            course TEXT NOT NULL DEFAULT 'General'
        );
        CREATE TABLE IF NOT EXISTS attendance (
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            status TEXT NOT NULL,
            PRIMARY KEY (student_id, day)
        );
        """
    )
    db.commit()
    db.close()


def percent(present, late, total):
    # Late counts as attended.
    return round(100 * (present + late) / total) if total else 0


@app.route("/")
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    total = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    counts = {s: 0 for s in STATUSES}
    for row in db.execute(
        "SELECT status, COUNT(*) c FROM attendance WHERE day=? GROUP BY status", (today,)
    ):
        counts[row["status"]] = row["c"]
    unmarked = total - sum(counts.values())
    low = db.execute(
        """SELECT s.name, s.roll_no,
                  SUM(a.status='Present') p, SUM(a.status='Late') l, COUNT(a.day) t
           FROM students s JOIN attendance a ON a.student_id = s.id
           GROUP BY s.id"""
    ).fetchall()
    at_risk = [
        {"name": r["name"], "roll_no": r["roll_no"], "pct": percent(r["p"], r["l"], r["t"])}
        for r in low
        if percent(r["p"], r["l"], r["t"]) < 75
    ]
    return render_template(
        "dashboard.html", today=today, total=total, counts=counts,
        unmarked=unmarked, at_risk=sorted(at_risk, key=lambda x: x["pct"]),
    )


@app.route("/students", methods=["GET", "POST"])
def students():
    db = get_db()
    if request.method == "POST":
        roll = request.form.get("roll_no", "").strip()
        name = request.form.get("name", "").strip()
        course = request.form.get("course", "").strip() or "General"
        if not roll or not name:
            flash("Roll number and name are both required.", "error")
        else:
            try:
                db.execute(
                    "INSERT INTO students (roll_no, name, course) VALUES (?, ?, ?)",
                    (roll, name, course),
                )
                db.commit()
                flash(f"Added {name}.", "ok")
            except sqlite3.IntegrityError:
                flash(f"Roll number {roll} already exists.", "error")
        return redirect(url_for("students"))
    rows = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    return render_template("students.html", students=rows)


@app.post("/students/<int:sid>/delete")
def delete_student(sid):
    db = get_db()
    db.execute("DELETE FROM attendance WHERE student_id=?", (sid,))
    db.execute("DELETE FROM students WHERE id=?", (sid,))
    db.commit()
    flash("Student removed.", "ok")
    return redirect(url_for("students"))


@app.route("/mark", methods=["GET", "POST"])
def mark():
    db = get_db()
    day = request.values.get("day") or date.today().isoformat()
    if request.method == "POST":
        for sid in request.form.getlist("sid"):
            status = request.form.get(f"status_{sid}")
            if status in STATUSES:
                db.execute(
                    "INSERT OR REPLACE INTO attendance (student_id, day, status) VALUES (?, ?, ?)",
                    (int(sid), day, status),
                )
        db.commit()
        flash(f"Attendance saved for {day}.", "ok")
        return redirect(url_for("mark", day=day))
    rows = db.execute(
        """SELECT s.id, s.roll_no, s.name, a.status
           FROM students s LEFT JOIN attendance a ON a.student_id = s.id AND a.day = ?
           ORDER BY s.roll_no""",
        (day,),
    ).fetchall()
    return render_template("mark.html", rows=rows, day=day, statuses=STATUSES)


@app.route("/report")
def report():
    db = get_db()
    days = [r[0] for r in db.execute(
        "SELECT DISTINCT day FROM attendance ORDER BY day DESC LIMIT 10")][::-1]
    studs = db.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    grid = []
    for s in studs:
        marks = {r["day"]: r["status"] for r in db.execute(
            "SELECT day, status FROM attendance WHERE student_id=?", (s["id"],))}
        p = sum(v == "Present" for v in marks.values())
        l = sum(v == "Late" for v in marks.values())
        grid.append({
            "student": s,
            "cells": [marks.get(d) for d in days],
            "pct": percent(p, l, len(marks)),
            "has_data": bool(marks),
        })
    return render_template("report.html", days=days, grid=grid)


@app.route("/health")
def health():
    return {"status": "ok"}, 200


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

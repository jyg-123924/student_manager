"""学生成绩管理系统 — 手机浏览器可用的 Web 版。"""

import os
import socket

from flask import Flask, flash, redirect, render_template, request, url_for

from student_manager import StudentManager

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "student-manager-mobile-dev")
manager = StudentManager()

SUBJECTS = ("语文", "数学", "英语", "计算机")


def _parse_scores(form) -> dict[str, float]:
    scores: dict[str, float] = {}
    for subject in SUBJECTS:
        raw = form.get(subject, "").strip()
        if raw:
            scores[subject] = float(raw)
    return scores


@app.route("/")
def index():
    keyword = request.args.get("q", "").strip()
    if keyword:
        students = manager.search_by_name(keyword)
    else:
        students = manager.list_all()
    return render_template("index.html", students=students, keyword=keyword)


@app.route("/add", methods=["GET", "POST"])
def add_student():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_no = request.form.get("student_no", "").strip()
        try:
            scores = _parse_scores(request.form)
            manager.add(name, student_no, scores)
            flash(f"已添加学生：{name}", "success")
            return redirect(url_for("index"))
        except (ValueError, KeyError) as e:
            flash(str(e), "error")
    return render_template("form.html", student=None, action="add")


@app.route("/edit/<student_id>", methods=["GET", "POST"])
def edit_student(student_id: str):
    student = manager.get(student_id)
    if student is None:
        flash("学生不存在", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_no = request.form.get("student_no", "").strip()
        try:
            scores = _parse_scores(request.form)
            manager.update(
                student_id,
                name=name or None,
                student_no=student_no or None,
                scores=scores,
            )
            flash(f"已更新学生：{name or student.name}", "success")
            return redirect(url_for("index"))
        except (ValueError, KeyError) as e:
            flash(str(e), "error")

    return render_template("form.html", student=student, action="edit")


@app.route("/delete/<student_id>", methods=["POST"])
def delete_student(student_id: str):
    try:
        student = manager.delete(student_id)
        flash(f"已删除学生：{student.name}", "success")
    except KeyError as e:
        flash(str(e), "error")
    return redirect(url_for("index"))


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


if __name__ == "__main__":
    ip = _local_ip()
    print("=" * 50)
    print("学生成绩管理系统 Web 版已启动")
    print(f"本机访问: http://127.0.0.1:5000")
    print(f"手机访问: http://{ip}:5000  (需同一 WiFi)")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)

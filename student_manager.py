"""学生成绩管理系统 — 支持增删改查，数据持久化到 JSON 文件。"""

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


DEFAULT_DATA_FILE = os.path.join(os.path.dirname(__file__), "students.json")
DEFAULT_TRASH_FILE = os.path.join(os.path.dirname(__file__), "trash.json")


@dataclass
class Student:
    """学生信息。"""

    name: str
    student_no: str
    scores: dict[str, float] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Student":
        return cls(
            id=data["id"],
            name=data["name"],
            student_no=data["student_no"],
            scores=data.get("scores", {}),
        )

    @property
    def average(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)


@dataclass
class TrashedStudent:
    """回收站中的学生记录。"""

    student: Student
    deleted_at: str

    def to_dict(self) -> dict[str, Any]:
        data = self.student.to_dict()
        data["deleted_at"] = self.deleted_at
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrashedStudent":
        deleted_at = data["deleted_at"]
        student_data = {k: v for k, v in data.items() if k != "deleted_at"}
        return cls(student=Student.from_dict(student_data), deleted_at=deleted_at)


class StudentManager:
    """学生成绩管理器，负责 CRUD 与 JSON 持久化。"""

    def __init__(
        self,
        data_file: str = DEFAULT_DATA_FILE,
        trash_file: str = DEFAULT_TRASH_FILE,
    ) -> None:
        self.data_file = data_file
        self.trash_file = trash_file
        self._students: dict[str, Student] = {}
        self._trash: dict[str, TrashedStudent] = {}
        self._load()
        self._load_trash()

    def _load(self) -> None:
        if not os.path.exists(self.data_file):
            self._save()
            return
        with open(self.data_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._students = {
            item["id"]: Student.from_dict(item) for item in raw
        }

    def _load_trash(self) -> None:
        if not os.path.exists(self.trash_file):
            self._save_trash()
            return
        with open(self.trash_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._trash = {
            item["id"]: TrashedStudent.from_dict(item) for item in raw
        }

    def _save(self) -> None:
        data = [s.to_dict() for s in self._students.values()]
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_trash(self) -> None:
        data = [t.to_dict() for t in self._trash.values()]
        with open(self.trash_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(
        self,
        name: str,
        student_no: str,
        scores: dict[str, float] | None = None,
    ) -> Student:
        """新增学生。"""
        if self.get_by_student_no(student_no):
            raise ValueError(f"学号 {student_no} 已存在")
        student = Student(name=name, student_no=student_no, scores=scores or {})
        self._students[student.id] = student
        self._save()
        return student

    def delete(self, student_id: str) -> Student:
        """将学生移入回收站（软删除）。"""
        student = self._students.pop(student_id, None)
        if student is None:
            raise KeyError(f"未找到 ID 为 {student_id} 的学生")
        trashed = TrashedStudent(
            student=student,
            deleted_at=datetime.now().isoformat(timespec="seconds"),
        )
        self._trash[student_id] = trashed
        self._save()
        self._save_trash()
        return student

    def delete_by_student_no(self, student_no: str) -> Student:
        """按学号将学生移入回收站。"""
        student = self.get_by_student_no(student_no)
        if student is None:
            raise KeyError(f"未找到学号为 {student_no} 的学生")
        return self.delete(student.id)

    def restore(self, student_id: str) -> Student:
        """从回收站恢复学生。"""
        trashed = self._trash.pop(student_id, None)
        if trashed is None:
            raise KeyError(f"回收站中未找到 ID 为 {student_id} 的学生")
        student = trashed.student
        if self.get_by_student_no(student.student_no):
            self._trash[student_id] = trashed
            self._save_trash()
            raise ValueError(
                f"学号 {student.student_no} 已被其他学生占用，无法恢复"
            )
        self._students[student.id] = student
        self._save()
        self._save_trash()
        return student

    def permanent_delete(self, student_id: str) -> Student:
        """从回收站彻底删除学生。"""
        trashed = self._trash.pop(student_id, None)
        if trashed is None:
            raise KeyError(f"回收站中未找到 ID 为 {student_id} 的学生")
        self._save_trash()
        return trashed.student

    def get_trashed(self, student_id: str) -> TrashedStudent | None:
        """查询回收站中的学生。"""
        return self._trash.get(student_id)

    def list_trash(self) -> list[TrashedStudent]:
        """返回回收站列表（最近删除的在前）。"""
        return sorted(
            self._trash.values(),
            key=lambda t: t.deleted_at,
            reverse=True,
        )

    def update(
        self,
        student_id: str,
        *,
        name: str | None = None,
        student_no: str | None = None,
        scores: dict[str, float] | None = None,
    ) -> Student:
        """更新学生信息（仅修改传入的字段）。"""
        student = self.get(student_id)
        if student is None:
            raise KeyError(f"未找到 ID 为 {student_id} 的学生")

        if student_no is not None and student_no != student.student_no:
            if self.get_by_student_no(student_no):
                raise ValueError(f"学号 {student_no} 已被其他学生使用")
            student.student_no = student_no

        if name is not None:
            student.name = name

        if scores is not None:
            student.scores.update(scores)

        self._save()
        return student

    def get(self, student_id: str) -> Student | None:
        """按 ID 查询学生。"""
        return self._students.get(student_id)

    def get_by_student_no(self, student_no: str) -> Student | None:
        """按学号查询学生。"""
        for student in self._students.values():
            if student.student_no == student_no:
                return student
        return None

    def list_all(self) -> list[Student]:
        """返回全部学生列表。"""
        return sorted(self._students.values(), key=lambda s: s.student_no)

    def search_by_name(self, keyword: str) -> list[Student]:
        """按姓名关键字模糊搜索。"""
        keyword = keyword.strip().lower()
        return [
            s for s in self._students.values()
            if keyword in s.name.lower()
        ]


def format_student(student: Student) -> str:
    """格式化单个学生的显示文本。"""
    scores_text = ", ".join(
        f"{subject}: {score}" for subject, score in sorted(student.scores.items())
    ) or "暂无成绩"
    return (
        f"ID: {student.id}\n"
        f"姓名: {student.name}\n"
        f"学号: {student.student_no}\n"
        f"成绩: {scores_text}\n"
        f"平均分: {student.average:.2f}"
    )


def _input_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("输入不能为空，请重试。")


def _input_scores() -> dict[str, float]:
    """交互式录入各科成绩。"""
    scores: dict[str, float] = {}
    print("录入成绩（直接回车结束）：")
    while True:
        subject = input("  科目名称: ").strip()
        if not subject:
            break
        while True:
            raw = input(f"  {subject} 分数: ").strip()
            try:
                score = float(raw)
                if 0 <= score <= 100:
                    scores[subject] = score
                    break
                print("分数应在 0~100 之间。")
            except ValueError:
                print("请输入有效数字。")
    return scores


def _print_students(students: list[Student]) -> None:
    if not students:
        print("暂无学生记录。")
        return
    for i, student in enumerate(students, 1):
        print(f"\n--- 第 {i} 条 ---")
        print(format_student(student))


def _handle_add(manager: StudentManager) -> None:
    name = _input_non_empty("姓名: ")
    student_no = _input_non_empty("学号: ")
    scores = _input_scores()
    try:
        student = manager.add(name, student_no, scores)
        print("\n添加成功！")
        print(format_student(student))
    except ValueError as e:
        print(f"\n添加失败: {e}")


def _handle_delete(manager: StudentManager) -> None:
    student_no = _input_non_empty("请输入要删除的学号: ")
    student = manager.get_by_student_no(student_no)
    if student is None:
        print(f"\n未找到学号为 {student_no} 的学生")
        return
    confirm = input(
        f"确定将 {student.name}（{student.student_no}）移入回收站吗？(y/n): "
    ).strip().lower()
    if confirm != "y":
        print("\n已取消删除。")
        return
    try:
        manager.delete(student.id)
        print(f"\n已移入回收站: {student.name} ({student.student_no})")
    except KeyError as e:
        print(f"\n删除失败: {e}")


def _handle_trash(manager: StudentManager) -> None:
    trashed = manager.list_trash()
    if not trashed:
        print("\n回收站为空。")
        return

    print("\n========== 回收站 ==========")
    for i, item in enumerate(trashed, 1):
        print(f"\n--- 第 {i} 条（删除于 {item.deleted_at}）---")
        print(format_student(item.student))

    print("\n1. 恢复  2. 彻底删除  0. 返回")
    choice = input("请选择: ").strip()
    if choice == "0":
        return

    student_no = _input_non_empty("请输入学号: ")
    target = None
    for item in trashed:
        if item.student.student_no == student_no:
            target = item
            break
    if target is None:
        print(f"\n回收站中未找到学号为 {student_no} 的学生")
        return

    if choice == "1":
        try:
            restored = manager.restore(target.student.id)
            print(f"\n已恢复学生: {restored.name} ({restored.student_no})")
        except (KeyError, ValueError) as e:
            print(f"\n恢复失败: {e}")
    elif choice == "2":
        confirm = input(
            f"确定彻底删除 {target.student.name} 吗？此操作不可恢复！(y/n): "
        ).strip().lower()
        if confirm != "y":
            print("\n已取消。")
            return
        try:
            manager.permanent_delete(target.student.id)
            print(f"\n已彻底删除: {target.student.name}")
        except KeyError as e:
            print(f"\n删除失败: {e}")
    else:
        print("无效选项。")


def _handle_update(manager: StudentManager) -> None:
    student_no = _input_non_empty("请输入要修改的学号: ")
    student = manager.get_by_student_no(student_no)
    if student is None:
        print(f"\n未找到学号为 {student_no} 的学生")
        return

    print(f"\n当前信息:\n{format_student(student)}")
    print("\n留空表示不修改该字段。")

    new_name = input(f"新姓名 [{student.name}]: ").strip()
    new_no = input(f"新学号 [{student.student_no}]: ").strip()

    update_scores = input("是否更新成绩? (y/n): ").strip().lower() == "y"
    scores = _input_scores() if update_scores else None

    try:
        updated = manager.update(
            student.id,
            name=new_name or None,
            student_no=new_no or None,
            scores=scores,
        )
        print("\n修改成功！")
        print(format_student(updated))
    except (KeyError, ValueError) as e:
        print(f"\n修改失败: {e}")


def _handle_query(manager: StudentManager) -> None:
    print("1. 查看全部  2. 按学号查询  3. 按姓名搜索")
    choice = input("请选择: ").strip()
    if choice == "1":
        _print_students(manager.list_all())
    elif choice == "2":
        student_no = _input_non_empty("学号: ")
        student = manager.get_by_student_no(student_no)
        if student:
            print(f"\n{format_student(student)}")
        else:
            print(f"\n未找到学号为 {student_no} 的学生")
    elif choice == "3":
        keyword = _input_non_empty("姓名关键字: ")
        _print_students(manager.search_by_name(keyword))
    else:
        print("无效选项。")


def main() -> None:
    manager = StudentManager()
    menu = """
========== 学生成绩管理系统 ==========
  1. 添加学生
  2. 删除学生
  3. 修改学生
  4. 查询学生
  5. 回收站
  0. 退出
======================================
"""
    actions = {
        "1": _handle_add,
        "2": _handle_delete,
        "3": _handle_update,
        "4": _handle_query,
        "5": _handle_trash,
    }

    print("欢迎使用学生成绩管理系统！")
    while True:
        print(menu)
        choice = input("请选择操作: ").strip()
        if choice == "0":
            print("再见！")
            break
        handler = actions.get(choice)
        if handler:
            handler(manager)
        else:
            print("无效选项，请重新输入。")


if __name__ == "__main__":
    main()

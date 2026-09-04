import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class WebProjectWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATA_DIR"] = cls.temp_dir.name
        os.environ["ADMIN_IDS"] = "1"
        source = Path(__file__).resolve().parents[1] / "kodbot_poro_max.py"
        spec = importlib.util.spec_from_file_location("kodbot_under_test", source)
        cls.bot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.bot)
        cls.bot.init_db()

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def setUp(self):
        with self.bot.get_db() as conn:
            conn.execute("DELETE FROM web_projects")
            conn.execute("DELETE FROM user_states")
            conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (100)")
            conn.commit()

    def _query(self):
        return {
            "id": "callback-id",
            "from": {"id": 100},
            "message": {"chat": {"id": 100}, "message_id": 10},
        }

    def _create_project(self):
        with self.bot.get_db() as conn:
            conn.execute(
                "INSERT INTO web_projects "
                "(user_id, project_name, name, html_code, css_code, js_code, html, css, js) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (100, "Test", "Test", "old html", "old css", "old js", "new html", "new css", "new js"),
            )
            project_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.commit()
        self.bot.set_state(100, "web_editing", {"project_id": project_id})
        return project_id

    def test_preview_uses_current_editable_fields(self):
        project_id = self._create_project()
        with patch.object(self.bot, "send_message"):
            self.bot.handle_web_preview(self._query())

        preview_path = self.bot.LOGS_DIR / f"web_preview_{project_id}.html"
        preview = preview_path.read_text(encoding="utf-8")
        self.assertIn("new html", preview)
        self.assertIn("new css", preview)
        self.assertIn("new js", preview)
        self.assertNotIn("old html", preview)

    def test_helper_changes_keep_legacy_fields_in_sync(self):
        project_id = self._create_project()
        with patch.object(self.bot, "edit_message"):
            self.bot.handle_web_add_element(self._query(), "heading")
            self.bot.handle_web_css_helper(self._query(), "color")
            self.bot.handle_web_js_snippet(self._query(), "alert")

        with self.bot.get_db() as conn:
            project = conn.execute("SELECT * FROM web_projects WHERE id=?", (project_id,)).fetchone()
        self.assertEqual(project["html"], project["html_code"])
        self.assertEqual(project["css"], project["css_code"])
        self.assertEqual(project["js"], project["js_code"])

    def test_delete_confirmation_uses_callback_project_not_stale_state(self):
        project_id = self._create_project()
        self.bot.set_state(100, "web_editing", {"project_id": project_id + 99})
        with patch.object(self.bot, "edit_message") as edit_message:
            self.bot.handle_web_delete_project(self._query(), project_id)

        keyboard = edit_message.call_args.kwargs["reply_markup"]
        self.assertEqual(keyboard["inline_keyboard"][0][0]["callback_data"], f"web_delete_confirm:{project_id}")


if __name__ == "__main__":
    unittest.main()

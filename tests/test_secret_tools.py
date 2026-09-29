import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from services.glados_service import GLaDOSService
from tools import update_secrets as menu


class GladosCookieTests(unittest.TestCase):
    def test_new_old_and_same_prefix_accounts(self):
        cookies = [
            "gld:sess=gld_fake1; gld:sess.sig=sameprefix-one",
            "gld:sess=gld_fake2; gld:sess.sig=sameprefix-two",
            "koa:sess=fake; koa:sess.sig=legacy12345678",
        ]
        with patch.dict(os.environ, {"GR_COOKIE": "||".join(cookies)}):
            configs = GLaDOSService().get_account_configs()
        self.assertEqual([c["cookie"] for c in configs], cookies)
        self.assertEqual(len({c["account_id"] for c in configs}), 3)
        self.assertEqual(configs[2]["account_id"], "legacy1234...")

    def test_requests_keep_cookie_unchanged(self):
        service = GLaDOSService()
        cookie = "gld:sess=gld_fake; gld:sess.sig=fake_signature"
        config = {"cookie": cookie, "base_url": "https://example.invalid"}
        with patch.object(service, "make_request") as request, redirect_stdout(io.StringIO()):
            request.return_value.json.return_value = {"code": 0, "data": {}}
            service.do_checkin(config)
            service.get_usage_info(config)
        self.assertEqual(request.call_count, 2)
        for call in request.call_args_list:
            self.assertEqual(call.kwargs["headers"]["cookie"], cookie)


class MenuTests(unittest.TestCase):
    def test_validation(self):
        mixed = "gld:sess=a; gld:sess.sig=b||koa:sess=c; koa:sess.sig=d"
        self.assertEqual(menu.validate_cookies(mixed, "GLaDOS"), (mixed, 2))
        self.assertEqual(menu.validate_cookies("session=a=b; uid=2", "iKuuu")[1], 1)
        for value in ("", "a=b||", "gld:sess=a", "gld:sess=a; koa:sess.sig=b", "a=b\r\nx=y"):
            with self.assertRaises(ValueError):
                menu.validate_cookies(value, "GLaDOS")

    def test_upload_each_service(self):
        accounts = [{"access_token": "fake", "user_id": "test"}]
        for choice, (service, secret_name) in menu.SERVICES.items():
            answers = [choice]
            if service != "WorkBuddy":
                answers.append("gld:sess=fake; gld:sess.sig=fakesig" if service == "GLaDOS" else "session=fake")
            answers.extend(["owner/repo", "y", "0"])
            with patch("builtins.input", side_effect=answers), patch.object(
                menu.exporter, "load_accounts", return_value=accounts
            ), patch.object(menu.exporter, "_describe_accounts"), patch.object(
                menu.exporter, "_get_github_token", return_value="fake-token"
            ), patch.object(menu.exporter, "update_github_secret") as upload, redirect_stdout(io.StringIO()):
                self.assertEqual(menu.main(["--auth-dir", "."]), 0)
            upload.assert_called_once()
            self.assertEqual(upload.call_args.args[:2], ("owner/repo", secret_name))
            self.assertEqual(upload.call_args.args[3], "fake-token")

    def test_cancel_never_uploads_or_reads_token(self):
        with patch("builtins.input", side_effect=["2", "session=fake", "owner/repo", "n", "0"]), patch.object(
            menu.exporter, "update_github_secret"
        ) as upload, patch.object(menu.exporter, "_get_github_token") as token, redirect_stdout(io.StringIO()):
            self.assertEqual(menu.main([]), 0)
        upload.assert_not_called()
        token.assert_not_called()

    def test_reject_copied_wrappers(self):
        for value in ('"session=fake"', "Cookie: session=fake", r"session=gld\_fake"):
            with self.assertRaises(ValueError):
                menu.validate_cookies(value, "iKuuu")

    def test_network_failure_returns_to_menu_without_secret_output(self):
        output = io.StringIO()
        with patch("builtins.input", side_effect=["2", "session=private-fake", "owner/repo", "y", "0"]), patch.object(
            menu.exporter, "_get_github_token", return_value="fake-token"
        ), patch.object(menu.exporter, "update_github_secret", side_effect=menu.exporter.requests.ConnectionError("private-fake")), redirect_stdout(output):
            self.assertEqual(menu.main([]), 0)
        self.assertIn("网络请求失败", output.getvalue())
        self.assertNotIn("private-fake", output.getvalue())


if __name__ == "__main__":
    unittest.main()

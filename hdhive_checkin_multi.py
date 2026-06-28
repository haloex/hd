#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import datetime as dt
import html
import json
import os
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


BASE_URL = "https://hdhive.com/"
CHECKIN_PATH = "/api/customer/user/checkin"


@dataclass
class Account:
    name: str
    cookie: str


@dataclass
class CheckinResult:
    name: str
    status: str
    message: str
    http_status: int | None = None


def parse_cookie_string(raw: str) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    ignored_attrs = {"path", "domain", "expires", "max-age", "secure", "httponly", "samesite"}
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        if not name or name.lower() in ignored_attrs:
            continue
        cookies.append(
            {
                "name": name,
                "value": value.strip(),
                "url": BASE_URL,
                "secure": True,
                "sameSite": "Lax",
            }
        )
    return cookies


def get_cookie_value(raw: str, name: str) -> str:
    for part in raw.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        cookie_name, value = part.split("=", 1)
        if cookie_name.strip() == name:
            return value.strip()
    return ""


def load_accounts() -> list[Account]:
    split_accounts: list[Account] = []
    for idx in range(1, 11):
        cookie = os.getenv(f"HDHIVE_COOKIE_{idx}", "").strip()
        if not cookie:
            continue
        name = os.getenv(f"HDHIVE_ACCOUNT_{idx}_NAME", "").strip() or f"account-{idx}"
        split_accounts.append(Account(name=name, cookie=cookie))
    if split_accounts:
        return split_accounts

    raw_accounts = os.getenv("HDHIVE_ACCOUNTS", "").strip()
    if raw_accounts:
        try:
            data = json.loads(raw_accounts)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"HDHIVE_ACCOUNTS is not valid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise SystemExit("HDHIVE_ACCOUNTS must be a JSON array.")

        accounts: list[Account] = []
        for idx, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise SystemExit(f"HDHIVE_ACCOUNTS item #{idx} must be an object.")
            cookie = str(item.get("cookie", "")).strip()
            if not cookie:
                raise SystemExit(f"HDHIVE_ACCOUNTS item #{idx} is missing cookie.")
            name = str(item.get("name") or f"account-{idx}").strip()
            accounts.append(Account(name=name, cookie=cookie))
        return accounts

    single_cookie = os.getenv("HDHIVE_COOKIE", "").strip()
    if single_cookie:
        return [Account(name=os.getenv("HDHIVE_ACCOUNT_NAME", "account-1"), cookie=single_cookie)]

    raise SystemExit("Set HDHIVE_COOKIE_1/HDHIVE_COOKIE_2, HDHIVE_ACCOUNTS, or HDHIVE_COOKIE in GitHub Secrets.")


def classify_response(payload: dict[str, Any]) -> tuple[str, str]:
    status = int(payload.get("status") or 0)
    data = payload.get("json") if isinstance(payload.get("json"), dict) else {}
    body = json.dumps(data, ensure_ascii=False) + "\n" + str(payload.get("text") or "")

    if status < 300 and (data.get("success") is True or data.get("code") in (0, "0", "success")):
        return "success", data.get("message") or data.get("description") or "签到成功"

    if any(word in body for word in ["已签到", "已经签到", "已经签", "重复", "明天再来"]):
        return "already", data.get("description") or data.get("message") or "今天已经签到过了"

    if status in (401, 403) or any(word in body.lower() for word in ["unauthorized", "forbidden", "invalid_session", "token"]):
        return "expired", data.get("description") or data.get("message") or "Cookie 可能已过期"

    return "failed", data.get("description") or data.get("message") or (str(payload.get("text") or "")[:300] or "签到失败")


def classify_direct_error(payload: dict[str, Any]) -> CheckinResult | None:
    error = str(payload.get("error") or "")
    code = str(payload.get("code") or "")
    merged = f"{error}\n{code}".lower()
    if any(
        marker.lower() in merged
        for marker in [
            "x-hdh-rsig",
            "invalid_session",
            "missing_signature",
            "signature_invalid",
            "unauthorized",
            "forbidden",
            "401",
            "403",
            "token",
            "cookie",
            "重新登录",
        ]
    ):
        return CheckinResult("unknown", "expired", "Cookie/session 可能已过期，请重新复制该账号 Cookie")
    return None


async def direct_signed_checkin(page: Any, user_id: str) -> dict[str, Any]:
    return await page.evaluate(
        """async ({ userId, checkinPath }) => {
          let req;
          self.webpackChunk_N_E = self.webpackChunk_N_E || [];
          self.webpackChunk_N_E.push([
            [Math.floor(Math.random() * 1e9)],
            {},
            function (r) { req = r; }
          ]);
          if (!req) return { ok: false, error: "webpack require unavailable" };

          function pickModule(id) {
            try {
              const mod = req(id);
              if (mod && typeof mod.t5 === "function") return mod;
            } catch (_) {}
            return null;
          }

          let mod = null;
          for (const cached of Object.values(req.c || {})) {
            const exports = cached && cached.exports;
            if (exports && typeof exports.t5 === "function") {
              mod = exports;
              break;
            }
          }
          if (!mod) mod = pickModule(9110);
          if (!mod && req.m) {
            for (const [id, factory] of Object.entries(req.m)) {
              const source = String(factory);
              if (
                source.includes("/api/customer/user/checkin") ||
                source.includes("signedFetch") ||
                source.includes("signRequest")
              ) {
                mod = pickModule(id);
                if (mod) break;
              }
            }
          }
          if (!mod || !mod.t5) {
            return { ok: false, error: "signedFetch export unavailable" };
          }
          if (mod.P$) mod.P$({ getUserId: () => userId || "0" });

          try {
            const response = await mod.t5(checkinPath, {
              method: "POST",
              credentials: "same-origin",
              cache: "no-store",
              headers: { "Content-Type": "application/json" },
              body: "{}"
            });
            const bytes = new Uint8Array(await response.arrayBuffer());
            const utf8 = new TextDecoder("utf-8").decode(bytes);
            let gb18030 = "";
            try { gb18030 = new TextDecoder("gb18030").decode(bytes); } catch (_) {}
            const text = !utf8.includes("\\uFFFD") ? utf8 : gb18030 || utf8;
            let parsed = null;
            for (const candidate of [text, utf8, gb18030]) {
              if (!candidate) continue;
              try {
                parsed = JSON.parse(candidate);
                break;
              } catch (_) {}
            }
            return {
              ok: true,
              status: response.status,
              text,
              json: parsed,
              headers: Object.fromEntries(response.headers.entries())
            };
          } catch (error) {
            return {
              ok: false,
              error: String(error),
              name: error && error.name,
              code: error && error.code
            };
          }
        }""",
        {"userId": user_id, "checkinPath": CHECKIN_PATH},
    )


async def check_one(browser: Any, account: Account) -> CheckinResult:
    context = await browser.new_context(
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        viewport={"width": 1366, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
    )
    try:
        cookies = parse_cookie_string(account.cookie)
        if not cookies:
            return CheckinResult(account.name, "failed", "Cookie 解析失败")

        await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45_000)
        await page.wait_for_timeout(5_000)

        payload = await direct_signed_checkin(page, get_cookie_value(account.cookie, "hdh_uid") or "0")
        if not payload.get("ok"):
            classified = classify_direct_error(payload)
            if classified:
                classified.name = account.name
                return classified
            return CheckinResult(account.name, "failed", f"直接签到接口不可用：{payload.get('error')}")

        status, message = classify_response(payload)
        return CheckinResult(account.name, status, message, int(payload.get("status") or 0))
    except Exception as exc:
        return CheckinResult(account.name, "failed", f"{type(exc).__name__}: {exc}")
    finally:
        await context.close()


def status_icon(status: str) -> str:
    return {
        "success": "SUCCESS",
        "already": "ALREADY",
        "expired": "EXPIRED",
        "failed": "FAILED",
    }.get(status, status.upper())


def build_report(results: list[CheckinResult]) -> str:
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"HDHive 签到结果 - {now} Asia/Shanghai", ""]
    for result in results:
        http = f" HTTP {result.http_status}" if result.http_status is not None else ""
        lines.append(f"[{status_icon(result.status)}] {result.name}{http}")
        lines.append(f"  {result.message}")
    return "\n".join(lines)


def send_telegram(message: str) -> None:
    token = os.getenv("TG_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TG_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TG_BOT_TOKEN or TG_CHAT_ID is not set; skip Telegram notification.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace")
        if response.status >= 300:
            raise RuntimeError(f"Telegram API HTTP {response.status}: {body}")


async def main() -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Missing dependency: playwright")
        print("Run: pip install playwright && python -m playwright install chromium")
        return 2

    accounts = load_accounts()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        try:
            results = []
            for account in accounts:
                print(f"Checking {account.name} ...")
                result = await check_one(browser, account)
                results.append(result)
                print(f"{account.name}: {result.status} - {result.message}")
        finally:
            await browser.close()

    report = build_report(results)
    print("")
    print(report)

    try:
        send_telegram(report)
    except Exception as exc:
        print(f"Telegram notification failed: {exc}")
        return 1

    return 0 if all(item.status in ("success", "already") for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

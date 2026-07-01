"""Command-line interface for TranslateDub AI.

Commands:
  translate  Translate + dub (or subtitle) a video in one shot.
  serve      Launch the local web UI in the default browser.
  config     Manage the Gemini key, Google Cloud credentials, and settings.
  version    Print the version.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from . import __version__, config


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _default_output(video_path: str, mode: str) -> str:
    stem, _ = os.path.splitext(os.path.basename(video_path))
    suffix = "subtitled" if mode == "subtitles_only" else "translated"
    directory = os.path.dirname(os.path.abspath(video_path))
    return os.path.join(directory, f"{stem}_{suffix}.mp4")


def cmd_translate(args: argparse.Namespace) -> int:
    from . import pipeline

    if not os.path.isfile(args.video):
        _log(f"Video not found: {args.video}")
        return 2

    gemini_key = config.get_secret("gemini_key")
    if not gemini_key:
        _log("No Gemini key. Set it with `translatedub config set-key` "
             "or the GEMINI_API_KEY environment variable.")
        return 2

    mode = "subtitles_only" if args.subtitles_only else "dubbed"
    output = args.output or _default_output(args.video, mode)

    voice_config = {}
    if args.engine == "google_cloud":
        creds = config.get_secret("google_cloud_credentials")
        if not creds:
            _log("google_cloud engine selected but no credentials stored.")
            return 2
        voice_config = {"credentials_json": creds, "voice_name": args.voice or ""}
    elif args.voice:
        voice_config = {"voice_name": args.voice}

    try:
        subtitles = pipeline.translate_video(
            args.video, args.src, args.to, gemini_key, log=_log
        )
        _log(f"Translated {len(subtitles)} subtitle lines.")
        pipeline.export_video(
            args.video, subtitles, output, mode=mode, engine=args.engine,
            target_lang=args.to, voice_config=voice_config, base_speed=args.speed,
            match_duration=not args.no_match_duration, original_vol=args.original_vol,
            dub_vol=args.dub_vol, burn_subtitles=args.burn_subtitles, log=_log,
        )
    except Exception as exc:  # noqa: BLE001 - top-level CLI error boundary
        _log(f"Error: {exc}")
        return 1

    print(output)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .web.server import serve

    serve(host=args.host, port=args.port, open_browser=not args.no_browser)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    if args.config_command == "path":
        print(config.config_file())
        return 0

    if args.config_command == "show":
        pub = config.public_config()
        for key, value in pub.items():
            print(f"{key}: {value}")
        return 0

    if args.config_command == "set-key":
        did_something = False
        if args.gemini or (not args.google_cloud_file):
            value = args.gemini or getpass.getpass("Gemini API key: ").strip()
            if value:
                config.set_secret("gemini_key", value)
                print("Gemini key stored at", config.config_file())
                did_something = True
        if args.google_cloud_file:
            if not os.path.isfile(args.google_cloud_file):
                _log(f"File not found: {args.google_cloud_file}")
                return 2
            with open(args.google_cloud_file, "r", encoding="utf-8") as f:
                config.set_secret("google_cloud_credentials", f.read())
            print("Google Cloud credentials stored.")
            did_something = True
        return 0 if did_something else 2

    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="translatedub",
        description="Local-first video translation, subtitling and AI dubbing.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("translate", help="Translate + dub (or subtitle) a video.")
    t.add_argument("video", help="Path to the input video.")
    t.add_argument("--to", default="vi", help="Target language code (default: vi).")
    t.add_argument("--src", "--from", default="auto", dest="src",
                   help="Source language code (default: auto).")
    t.add_argument("-o", "--output", help="Output video path.")
    t.add_argument("--engine", choices=("edge", "gtts", "google_cloud"), default="edge",
                   help="TTS engine (default: edge — free neural voices).")
    t.add_argument("--voice", help="Voice name (edge, e.g. vi-VN-HoaiMyNeural; "
                                    "or Google Cloud, e.g. vi-VN-Neural2-A).")
    t.add_argument("--speed", type=float, default=1.0, help="Base speaking speed.")
    t.add_argument("--no-match-duration", action="store_true",
                   help="Do not speed speech to fit subtitle timing.")
    t.add_argument("--original-vol", type=float, default=0.1,
                   help="Original audio volume 0-1 (default: 0.1).")
    t.add_argument("--dub-vol", type=float, default=1.0,
                   help="Dubbed audio volume 0-1 (default: 1.0).")
    t.add_argument("--burn-subtitles", action="store_true", help="Burn subtitles in.")
    t.add_argument("--subtitles-only", action="store_true",
                   help="Export subtitles without dubbing.")
    t.set_defaults(func=cmd_translate)

    s = sub.add_parser("serve", help="Launch the web UI in your browser.")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=0, help="Port (0 = auto).")
    s.add_argument("--no-browser", action="store_true", help="Do not open a browser.")
    s.set_defaults(func=cmd_serve)

    c = sub.add_parser("config", help="Manage credentials and settings.")
    csub = c.add_subparsers(dest="config_command", required=True)
    ck = csub.add_parser("set-key", help="Store the Gemini key / Google Cloud creds.")
    ck.add_argument("--gemini", help="Gemini API key (omit to be prompted).")
    ck.add_argument("--google-cloud-file", help="Path to a service-account JSON file.")
    csub.add_parser("show", help="Show non-secret settings and key presence.")
    csub.add_parser("path", help="Print the config file path.")
    c.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)

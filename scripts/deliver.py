#!/usr/bin/env python3
#
# BriefBot Delivery: Standalone email + audio delivery
# Reads synthesized content from a file and delivers via email and/or audio.
#
# Invocation pattern:
#     python deliver.py --content PATH [--email ADDRESS] [--audio] [--subject "..."]
#

import argparse
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure library modules are discoverable
MODULE_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MODULE_ROOT))

from lib import email_sender, env, tts


def main():
    parser = argparse.ArgumentParser(
        description="Deliver BriefBot synthesis via email and/or audio"
    )
    parser.add_argument(
        "--content",
        type=str,
        required=True,
        help="Path to the synthesized briefing markdown file",
    )
    parser.add_argument(
        "--email",
        type=str,
        metavar="ADDRESS",
        help="Email the briefing to this address (comma-separated for multiple)",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate MP3 audio of the briefing",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default="BriefBot Briefing",
        help="Email subject line",
    )
    args = parser.parse_args()

    # Read the synthesized content
    content_path = Path(args.content)
    if not content_path.exists():
        print("Error: Content file not found: {}".format(content_path), file=sys.stderr)
        sys.exit(1)

    briefing_text = content_path.read_text(encoding="utf-8")
    if not briefing_text.strip():
        print("Error: Content file is empty: {}".format(content_path), file=sys.stderr)
        sys.exit(1)

    config = env.get_config()
    audio_path = None

    # Generate audio first so it can be attached to the email
    if args.audio:
        try:
            output_dir = MODULE_ROOT.parent / "output"
            audio_path = output_dir / "briefbot.mp3"
            tts.generate_audio(
                briefing_text,
                audio_path,
                elevenlabs_api_key=config.get("ELEVENLABS_API_KEY"),
                elevenlabs_voice_id=config.get("ELEVENLABS_VOICE_ID"),
            )
            print("Audio saved to {}".format(audio_path))
        except Exception as err:
            print("Audio generation failed: {}".format(err), file=sys.stderr)
            audio_path = None

    # Send email
    if args.email:
        smtp_error = email_sender.validate_smtp_config(config)
        if smtp_error:
            print("Error: {}".format(smtp_error), file=sys.stderr)
            sys.exit(1)

        try:
            email_sender.send_report_email(
                recipient=args.email,
                subject=args.subject,
                markdown_body=briefing_text,
                config=config,
                audio_path=audio_path,
            )
            recipients = email_sender.parse_recipients(args.email)
            print("Email sent to {}".format(", ".join(recipients)))
        except Exception as err:
            print("Email failed: {}".format(err), file=sys.stderr)
            sys.exit(1)

    if not args.audio and not args.email:
        print("Nothing to deliver. Use --audio and/or --email.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

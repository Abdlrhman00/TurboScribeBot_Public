import argparse
import json
import os
from dotenv import load_dotenv
from turboscribe_bot import TurboScribeBot
import time
import sys
#from helper import period_delete

load_dotenv()  # loads from .env

email = os.getenv("EMAIL")
password = os.getenv("PASSWORD")
days = os.getenv("DAY")
HOST_OUTPUTS_BASE = os.getenv("HOST_OUTPUTS_BASE")

def parse_args():
    parser = argparse.ArgumentParser(description="TurboScribe Automation Script")

    parser.add_argument("--id", required=True, help="ID of the process")
    parser.add_argument("--output", required=True, help="the path of the output folder")

    # Source workflow (Zoom/OneDrive)
    parser.add_argument(
        "--source",
        choices=["zoom", "onedrive"],
        help="Choose the source of the link"
    )
    parser.add_argument("--passcode", help="Passcode for Zoom recording if required")
    parser.add_argument("--with-transcription", action="store_true", help="Download and transcribe after download")

    # Direct transcription workflow (no --source)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--link", help="Link to audio/video file (YouTube, etc.)")
    group.add_argument("--file", help="Path to local audio/video file")

    # Options
    parser.add_argument("--language", help="Language of transcription")
    parser.add_argument("--model", default="base", choices=["base", "small", "large-v2"], help="Transcription model")
    parser.add_argument("--owner", help="Change owner of the folder")

    # Features (flags)
    parser.add_argument(
        "--speakers",
        type=int,
        nargs="?",
        const=-1,
        help="Enable speaker recognition (optionally pass number of speakers, default: auto detect)"
    )
    parser.add_argument("--transcribe", action="store_true", help="Enable transcription")
    parser.add_argument("--restore", action="store_true", help="Restore audio quality")
    parser.add_argument("--timestamps", action="store_true", help="Add timestamps")
    parser.add_argument("--short_summary", action="store_true", help="Summarize (short)")
    parser.add_argument("--detail_summary", action="store_true", help="Summarize (detailed)")
    parser.add_argument("--translate", help="Translate output with Google Translate")
    parser.add_argument("--download_audio", action="store_true", help="Download audio file")

    args = parser.parse_args()

    # --- Validation logic ---
    if args.source:
        # Zoom/OneDrive flow
        if args.with_transcription and not args.language:
            parser.error("--language is required when using --with-transcription")
    else:
        # Direct transcription flow
        if not (args.link or args.file):
            parser.error("Must provide --link or --file if --source is not specified")
        if not args.language:
            parser.error("--language is required when using --link or --file")

    return args

# def parse_args():
#     parser = argparse.ArgumentParser(description="TurboScribe Automation Script")

#     # Required
#     # parser.add_argument("--email", required=True, help="Login email")
#     # parser.add_argument("--password", required=True, help="Login password")
#     parser.add_argument("--id", required=True, help="id of the proccess")

#     group = parser.add_mutually_exclusive_group(required=True)
#     group.add_argument("--link", help="link to audio file")
#     group.add_argument("--file", help="Path to audio file")

#     # parser.add_argument("--link", required=True, help="link to audio file")
#     # parser.add_argument("--file", required=True, help="Path to audio file")

#     parser.add_argument(
#     "--source", 
#     choices=["zoom", "onedrive"], 
#     required=True, 
#     help="Choose the source of the link"
#     )


#     parser.add_argument("--with-transcription", action="store_true", help="Enable recognize speakers")
#     parser.add_argument("--passcode", help="Passcode for Zoom recording if required")

#     # Options
#     parser.add_argument("--language", required=True, help="Language of transcription")
#     parser.add_argument("--model", default="base", choices=["base", "small", "large-v2"], help="Transcription model")

#     # Features (flags)
#     parser.add_argument(
#     "--speakers",
#     type=int,
#     nargs="?",
#     const=-1,
#     help="Enable recognize speakers (optionally pass number of speakers, default: auto detect)"
#     )

#     parser.add_argument("--transcribe", action="store_true", help="Enable recognize speakers")
#     parser.add_argument("--restore", action="store_true", help="Enable restore audio")

#     parser.add_argument("--timestamps", action="store_true", help="Enable timestamps")
#     parser.add_argument("--short_summary", action="store_true", help="Summarize with GPT")
#     parser.add_argument("--detail_summary", action="store_true", help="Summarize with GPT")

#     parser.add_argument("--translate", help="Translate with Google Translate")

#     #parser.add_argument("--translate", action="store_true", help="Translate with Google Translate")
#     parser.add_argument("--download_audio", action="store_true", help="Download audio file")

#     return parser.parse_args()

if __name__ == "__main__":
    try:
        #period_delete(days)

        args = parse_args()

        # Convert args into dict for the bot
        options = {
            "language": args.language,
            "model": args.model,
            "recognize_speakers": args.speakers,
            "transcribe": args.transcribe,
            "restore_audio": args.restore,
            "timestamps": args.timestamps,
            "short_summary": args.short_summary,
            "detail_summary": args.detail_summary,
            "translate": args.translate,
            "download_audio": args.download_audio,
        }

        output_dir = os.path.join(args.output, f"{args.id}")
        os.makedirs(output_dir, exist_ok=True)

        bot = TurboScribeBot(args.id, email, password, options, output_dir)

        bot.start_browser(True)
        bot.generate_report(output_dir, args.id)

        if args.source:
            args.file = bot.external_links(args.source, args.link, args.passcode)
            print(args.file)

            if not args.with_transcription:
                bot.generate_report(output_dir, args.id, True)
                sys.exit(1)

        bot.login()
        time.sleep(1)

        bot.open_language_menu()
        bot.switch_to_arabic()
        time.sleep(2)

        if args.link and not args.source:
            bot.import_from_link(args.link)
        elif args.file:
            bot.upload_file(args.file)
        
        bot.select_options()
        time.sleep(1)

        bot.start_transcription()
        time.sleep(1)

        bot.monitor_proccess()
        time.sleep(1)

        if args.timestamps:
            bot.export_download(output_dir, args.id)
        else:
            bot.download_results(output_dir, args.id)
        time.sleep(1)

        if args.download_audio:
            bot.download_audio(output_dir, args.id)
            time.sleep(1)

        if args.short_summary or args.detail_summary:
            bot.chatgpt_click()
            time.sleep(0.5)

            if args.short_summary:
                bot.generate_short_summary(output_dir, args.id)

            if args.detail_summary:
                bot.generate_detailed_summary(output_dir, args.id)

            bot.close_chatgpt()
            time.sleep(0.5)


        if args.translate:
            bot.translate(args.translate, output_dir, args.id)

        if args.owner:
            bot.change_owner(output_dir, args.owner)

        bot.generate_report(output_dir, args.id, True)

        print("✅ Job finished successfully!")
        
    except Exception as e:
        print(f"❌ Error in main(): {e}")
        import traceback
        traceback.print_exc()

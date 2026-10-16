from datetime import datetime
import os
import traceback


def write_log(message):
    os.makedirs("logs", exist_ok=True)

    log_file = f"logs/{datetime.now().strftime('%Y%m%d')}.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = f"{timestamp} - {message}"

    print(line)

    with open(log_file, "a", encoding="utf-8") as file:
        file.write(line + "\n")


def write_exception(ex):

    write_log("========== ERROR ==========")

    write_log(str(ex))

    write_log(traceback.format_exc())

    write_log("===========================")
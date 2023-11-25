import json
import os
from typing import Dict

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import mplcyberpunk
import pandas as pd
import requests
from pandas import DataFrame
from telegram.ext import CallbackContext

plt.style.use("cyberpunk")


def read_csv(outdir: str, csv_name, df_columns) -> pd.DataFrame:
    try:
        df = pd.read_csv(os.path.join(outdir, f"{csv_name}.csv"), names=df_columns)
        df = df.astype({"timestamp": "datetime64[s]"})
    except Exception:
        df = pd.DataFrame(columns=df_columns)

    return df


def write_csv(df, outdir: str, csv_name):
    df.to_csv(os.path.join(outdir, f"{csv_name}.csv"), header=True, index=False)


def read_config(outdir: str) -> Dict:
    with open(f"{outdir}/env.json") as file:
        config = json.load(file)
    return config


def run_request(
    request_type: str,
    url: str,
    request_body: Dict[str, str] = {},
    request_json: str = "",
    bearer="",
    timeout: int = 30,
    media: Dict = None,
    request_headers=None,
    num_of_tries=1,
) -> Dict:
    success = False
    response = None
    expected_status_code = None
    try_number = 1

    while not success and try_number <= num_of_tries:
        try_number = try_number + 1
        try:
            if request_type == "GET":
                expected_status_code = 200
                if request_headers is None:
                    request_headers = {
                        "Content-Type": "application/json",
                        "Authorization": bearer,
                    }
                response = requests.get(
                    url=url,
                    headers=request_headers,
                    params=request_body,
                    timeout=timeout,
                )
            elif request_type == "POST":
                expected_status_code = 200
                if media is not None:
                    response = requests.post(
                        url, request_body, files=media, timeout=timeout
                    )
                else:
                    response = requests.post(
                        url=url,
                        headers={"Content-Type": "application/json"},
                        json=request_body,
                        timeout=timeout,
                    )
            elif request_type == "PATCH":
                expected_status_code = 200
                response = requests.patch(
                    url=url,
                    headers={"Content-Type": "application/json"},
                    data=request_json,
                    timeout=timeout,
                )
            else:
                raise Exception("Wrong request type!")
            success = True
        except Exception as e:
            print(e)

    if not success:
        raise Exception(f"The request failed {num_of_tries} times.")

    if response.status_code != expected_status_code:
        raise Exception(response.content.decode("UTF-8"))

    return json.loads(response.content.decode("UTF-8"))


async def plot_exercises(
    all_exercises: DataFrame, hashed_id: str, chat_id: int, context: CallbackContext
):
    plt.rcParams.update({"font.size": 22})
    for c in all_exercises["exercise"].unique():
        if c in ["Pullup overhand", "Pullup underhand", "Pushup", "The Countdown"]:
            plot_value = "reps"
        else:
            plot_value = "kg"
        resampled = all_exercises.drop("group", axis=1)
        resampled = resampled[resampled.exercise == c].drop("exercise", axis=1)
        drawstyle = "default"
        fig, ax = plt.subplots(figsize=(15, 15))
        ax.plot(resampled.timestamp, resampled[plot_value], drawstyle=drawstyle)
        ax.scatter(resampled.timestamp, resampled[plot_value])
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m. %H:%M"))
        plt.gcf().autofmt_xdate()
        plt.ylabel(plot_value)
        plt.xlabel("Date")
        plt.title(c)

        for i, point in resampled.iterrows():
            if plot_value == "kg":
                annotation = f'{point["kg"]} kg ({point["reps"]} reps)'
            else:
                annotation = f'{point["reps"]} reps'
            ax.annotate(
                annotation,
                (point["timestamp"], point[plot_value]),
                xytext=(10, -5),
                textcoords="offset points"
            )

        mplcyberpunk.add_glow_effects()
        plt.savefig(f"{hashed_id}_{c}.png")

        await context.bot.send_photo(chat_id, f"{hashed_id}_{c}.png")

        plt.cla()
        plt.clf()
        plt.close("all")

    return all_exercises["exercise"].unique()

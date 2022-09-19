from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from st_aggrid import AgGrid

DATA_DIR = Path(__file__).parent / "data"
FILE_PREFIX = "tab_wfa"
PLOT_PERCENTILES = ["P3", "P10", "P25", "P50", "P75", "P90", "P97"]
PERCENTILE_DASHES = ["P3", "P25", "P75", "P97"]


class Gender(Enum):
    boys = "gutt"
    girls = "jente"


class GenderAlias(Enum):
    boys = "boys"
    girls = "girls"


class Age(Enum):
    zero_to_thirteen_weeks = "0 - 13 uker"
    zero_to_five_years = "0 - 5 år"


class AgeAlias(Enum):
    zero_to_thirteen_weeks = "0_13"
    zero_to_five_years = "0_5"


class ColumnNames(Enum):
    date = "dato (DD-MM-YYYY)"
    weight = "vekt (gram)"


@st.cache
def read_percentiles(gender, age):
    file_path = DATA_DIR / f"{FILE_PREFIX}_{gender}_p_{age}.xlsx"
    return pd.read_excel(file_path, index_col=0)[PLOT_PERCENTILES]


@st.cache
def create_style_dict():
    line_style = {percentile: dict(color="black", width=1) for percentile in PLOT_PERCENTILES}
    line_style["P50"]["width"] = 3
    for percentile in PERCENTILE_DASHES:
        line_style[percentile]["dash"] = "dash"
    return line_style


def percentile_plot(percentiles, line_style):
    fig = go.Figure()
    x_name = "Uke" if chosen_age == Age.zero_to_thirteen_weeks.value else "Måned"
    hovertext = "%{text}: %{x}<br>Vekt: %{y:.2f} kg<extra></extra>"
    for percentile in percentiles.columns:
        fig.add_trace(
            go.Scatter(
                x=percentiles.index,
                y=percentiles[percentile],
                line=line_style[percentile],
                mode="lines",
                name=percentile,
                hovertemplate=hovertext,
                text=[x_name] * len(percentiles.index),
            )
        )
        fig.add_annotation(
            x=percentiles.index.max(),
            y=percentiles.loc[percentiles.index.max(), percentile],
            text=percentile,
            showarrow=False,
            xshift=15,
        )
    return fig.update_layout(xaxis_title=x_name, yaxis_title="Vekt", showlegend=False)


def response_to_df(response, age):
    days_in_time_unit = 7 if age == Age.zero_to_thirteen_weeks.value else 30.5
    measurements = response["data"]
    measurements = measurements.rename(
        columns={
            ColumnNames.date.value: ColumnNames.date.name,
            ColumnNames.weight.value: ColumnNames.weight.name,
        }
    )
    measurements = measurements.replace("", pd.NaT)
    measurements = measurements.dropna(how="any")
    measurements[ColumnNames.date.name] = pd.to_datetime(
        measurements[ColumnNames.date.name], dayfirst=True
    )
    measurements[ColumnNames.weight.name] = (measurements[ColumnNames.weight.name]).astype(
        int
    ) / 1000
    measurements = measurements.sort_values(ColumnNames.date.name)
    measurements["time_unit"] = (
        pd.TimedeltaIndex(
            measurements[ColumnNames.date.name] - measurements[ColumnNames.date.name].iloc[0]
        ).days
        / days_in_time_unit
    )
    return measurements


def add_measurements_to_plot(fig):
    fig.add_trace(
        go.Scatter(
            x=measurements["time_unit"],
            y=measurements[ColumnNames.weight.name],
            line=dict(color="red", width=3),
            mode="lines",
            hovertemplate="Dato:%{text}<br>Vekt: %{y:.2f} kg<extra></extra>",
            text=pd.DatetimeIndex(measurements[ColumnNames.date.name]).strftime("%d-%m-%Y"),
        )
    )
    return fig


line_style = create_style_dict()

gender_keys = {
    Gender.boys.value: GenderAlias.boys.value,
    Gender.girls.value: GenderAlias.girls.value,
}
age_keys = {
    Age.zero_to_five_years.value: AgeAlias.zero_to_five_years.value,
    Age.zero_to_thirteen_weeks.value: AgeAlias.zero_to_thirteen_weeks.value,
}

chosen_gender = st.radio("Velg kjønn", [Gender.boys.value, Gender.girls.value])
gender = gender_keys[chosen_gender]
chosen_age = st.radio(
    "Velg persentil-skjema",
    [Age.zero_to_thirteen_weeks.value, Age.zero_to_five_years.value],
)
age = age_keys[chosen_age]

percentiles = read_percentiles(gender, age)
fig = percentile_plot(percentiles, line_style)

number_of_measurements = int(st.number_input(label="Velg antall vektmålinger", value=5))

df_template = pd.DataFrame(
    [["", np.nan]] * number_of_measurements,
    index=range(number_of_measurements),
    columns=[ColumnNames.date.value, ColumnNames.weight.value],
)

with st.form("measurements") as f:
    st.header("Vektmålinger")
    response = AgGrid(df_template, editable=True, fit_columns_on_grid_load=True)
    st.form_submit_button()


if response["data"][ColumnNames.weight.value].notnull().sum() > 1:

    measurements = response_to_df(response, age)

    fig = add_measurements_to_plot(fig)

st.write(fig)

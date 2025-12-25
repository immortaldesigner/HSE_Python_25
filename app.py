import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import plotly.express as px

st.title("Анализ температурных данных и мониторинг текущей температуры")

uploaded_file = st.file_uploader(
    "Загрузите CSV файл с историческими данными",
    type="csv"
)

if uploaded_file:
    df = pd.read_csv(uploaded_file, parse_dates=["timestamp"])
    df = df.sort_values(["city", "timestamp"])

    cities = df["city"].unique()
    selected_city = st.selectbox("Выберите город", cities)
    df_city = df[df["city"] == selected_city].copy()

    # Статистика
    st.subheader(f"Статистика по историческим данным - {selected_city}")
    st.dataframe(df_city.describe())

    df_city["rolling_mean_30"] = (
        df_city["temperature"]
        .rolling(window=30, min_periods=1)
        .mean()
    )

    season_stats = (
        df_city.groupby("season")["temperature"]
        .agg(["mean", "std"])
        .rename(columns={"mean": "mean_temp", "std": "std_temp"})
    )

    df_city = df_city.merge(season_stats, on="season", how="left")

    df_city["is_anomaly"] = (
        (df_city["temperature"] > df_city["mean_temp"] + 2 * df_city["std_temp"]) |
        (df_city["temperature"] < df_city["mean_temp"] - 2 * df_city["std_temp"])
    )

    # Аномалии
    st.subheader("Временной ряд температур")

    fig = px.line(
        df_city,
        x="timestamp",
        y="temperature",
        title=f"Температуры в {selected_city}"
    )

    fig.add_scatter(
        x=df_city[df_city["is_anomaly"]]["timestamp"],
        y=df_city[df_city["is_anomaly"]]["temperature"],
        mode="markers",
        marker=dict(color="red", size=6),
        name="Аномалии"
    )

    st.plotly_chart(fig)

    # Сезонные профили
    st.subheader("Сезонные профили")

    season_avg = df_city.groupby("season")["temperature"].mean()
    season_std = df_city.groupby("season")["temperature"].std()

    fig_season = px.bar(
        x=season_avg.index,
        y=season_avg.values,
        error_y=season_std.values,
        labels={"x": "Сезон", "y": "Средняя температура"},
        title=f"Сезонный профиль - {selected_city}"
    )

    st.plotly_chart(fig_season)

    # Проверка по API
    st.subheader("Текущая температура через OpenWeatherMap")

    api_key = st.text_input(
        "Введите ваш OpenWeatherMap API ключ",
        type="password"
    )

    if api_key:
        month_to_season = {
            12: "winter", 1: "winter", 2: "winter",
            3: "spring", 4: "spring", 5: "spring",
            6: "summer", 7: "summer", 8: "summer",
            9: "autumn", 10: "autumn", 11: "autumn"
        }

        current_season = month_to_season[datetime.now().month]

        url = (
            "http://api.openweathermap.org/data/2.5/weather"
            f"?q={selected_city}&appid={api_key}&units=metric"
        )

        resp = requests.get(url)
        data = resp.json()

        if resp.status_code == 200:
            current_temp = data["main"]["temp"]

            season_stats_current = (
                df_city[df_city["season"] == current_season]["temperature"]
                .agg(["mean", "std"])
            )

            mean_temp = season_stats_current["mean"]
            std_temp = season_stats_current["std"]

            status = (
                "Аномальная"
                if (
                    current_temp > mean_temp + 2 * std_temp or
                    current_temp < mean_temp - 2 * std_temp
                )
                else "Адекватная"
            )

            st.write(
                f"Текущая температура в **{selected_city}**: "
                f"**{current_temp:.1f}°C** — {status}"
            )

        elif resp.status_code == 401:
            st.error(
                "Неверный API ключ "
                "(401: Invalid API key)"
            )
        else:
            st.error(f"Ошибка запроса: {data}")

    # Дополнительные функции
    # REFERENCE https://habr.com/ru/articles/668672/

    st.header("Дополнительные функции")

    #Сравнение нескольких городов
    st.subheader("Сравнение температур между городами")

    selected_cities_multi = st.multiselect(
        "Выберите города",
        options=cities,
        default=[selected_city]
    )

    if selected_cities_multi:
        df_multi_city = df[df["city"].isin(selected_cities_multi)]

        fig_cities = px.line(
            df_multi_city,
            x="timestamp",
            y="temperature",
            color="city",
            title="Сравнение температур между городами"
        )

        st.plotly_chart(fig_cities)
    else:
        st.info("Выберите хотя бы один город.")


    #Сравнение нескольких годов
    st.subheader("Сравнение температур по годам (наложение)")

    df_city["year"] = df_city["timestamp"].dt.year
    df_city["day_of_year"] = df_city["timestamp"].dt.dayofyear

    available_years = sorted(df_city["year"].unique())

    selected_years = st.multiselect(
        "Выберите годы для сравнения",
        options=available_years,
        default=available_years[:2]
        if len(available_years) >= 2
        else available_years
    )

    if selected_years:
        df_years = df_city[df_city["year"].isin(selected_years)]

        fig_years = px.line(
            df_years,
            x="day_of_year",
            y="temperature",
            color="year",
            labels={"day_of_year": "День года"},
            title=f"Наложение температур по годам - {selected_city}"
        )

        st.plotly_chart(fig_years)
    else:
        st.info("Выберите хотя бы один год для отображения.")

    #live map
    #Вдохновился https://github.com/das88768/Weather_Forecaster_streamlit
    ## и https://towardsdatascience.com/3-easy-ways-to-include-interactive-maps-in-a-streamlit-app-b49f6a22a636/
    st.subheader("Интерактивная карта текущей погоды")

    if not api_key:
        st.info("Введите API ключ выше, чтобы отобразить карту текущей погоды.")
    else:
        weather_data = []

        for city in cities:
            url = (
                "http://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={api_key}&units=metric"
            )

            resp = requests.get(url)
            data = resp.json()

            if resp.status_code == 200:
                weather_data.append({
                    "city": city,
                    "lat": data["coord"]["lat"],
                    "lon": data["coord"]["lon"],
                    "temperature": data["main"]["temp"]
                })

        if weather_data:
            map_df = pd.DataFrame(weather_data)
            map_df["marker_size"] = map_df["temperature"].abs() + 5

            fig_map = px.scatter_mapbox(
                map_df,
                lat="lat",
                lon="lon",
                color="temperature",
                size="marker_size",
                hover_name="city",
                hover_data={"temperature": ":.1f"},
                color_continuous_scale="RdBu_r",
                zoom=1,
                height=500,
                title="Текущая температура в городах"
            )

            fig_map.update_layout(
                mapbox_style="open-street-map",
                margin=dict(l=0, r=0, t=40, b=0)
            )

            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Не удалось получить данные для отображения карты.")
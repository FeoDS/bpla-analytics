import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Дашборд БПЛА", layout="wide")
st.title("Аналитика: Активность БПЛА")

# === ВАША ССЫЛКА НА GOOGLE ТАБЛИЦУ ===
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1gFjEc-wc7a3SHn3pK2cEm9m0gihAz93G/edit?usp=sharing&ouid=105336077872687698779&rtpof=true&sd=true"

@st.cache_data(ttl=60) # Сайт проверяет обновления раз в 60 секунд
def load_data(url):
    # Умный конвертер ссылки для скачивания данных
    if "/edit" in url:
        export_url = url.split('/edit')[0] + '/export?format=xlsx'
    else:
        export_url = url
    return pd.ExcelFile(export_url)

try:
    # 1. Загружаем данные по ссылке
    xls = load_data(GOOGLE_SHEET_URL)
    sheet_names = xls.sheet_names
    
    # 2. Выбор вкладки (даты)
    selected_date = st.selectbox("📅 Выберите вкладку (дату):", sheet_names)
    
    # 3. Читаем выбранный лист
    df = pd.read_excel(xls, sheet_name=selected_date, header=None)
    raw_data = df.values.tolist()

    if len(raw_data) < 3:
        st.warning("На этой вкладке пока нет данных.")
        st.stop()

    # --- Наш алгоритм поиска и сбора цифр ---
    locations_row = raw_data[1]
    types_row = raw_data[2]

    current_loc = "Неизвестно"
    for i in range(2, len(locations_row)):
        val = str(locations_row[i]).strip()
        if val not in ['nan', 'None', '', '[ПУСТО]']:
            current_loc = val
        locations_row[i] = current_loc

    parsed_data = []
    for row_idx in range(3, len(raw_data)):
        row = raw_data[row_idx]
        time_val = str(row[0]).strip()
        
        if time_val in ['nan', 'None', '', '[ПУСТО]']:
            continue

        for col_idx in range(2, len(row)):
            loc = locations_row[col_idx]
            typ = str(types_row[col_idx]).strip()
            val = str(row[col_idx]).strip()
            
            if val not in ['nan', 'None', '', '[ПУСТО]']:
                clean_val = ''.join(filter(str.isdigit, val))
                if clean_val:
                    qty = int(clean_val)
                    if qty > 0:
                        parsed_data.append({
                            'Время': time_val,
                            'Место': loc,
                            'Тип': typ,
                            'Количество': qty
                        })

    df_cleaned = pd.DataFrame(parsed_data)

    # --- Отрисовка графика ---
    if len(df_cleaned) == 0:
        st.info("В выбранный день активность не зафиксирована.")
    else:
        st.success(f"Общее количество зафиксированных меток: **{df_cleaned['Количество'].sum()}**")
        
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

        locations_list = df_cleaned['Место'].unique().tolist()
        types_list = df_cleaned['Тип'].unique().tolist()

        y_map = {loc: i for i, loc in enumerate(locations_list)}
        y_offsets = {'Яга': -0.2, 'Мавик': 0.0, 'ФПВ': 0.2}
        colors = {'Яга': 'red', 'Мавик': 'blue', 'ФПВ': 'green'}

        fig, ax = plt.subplots(figsize=(14, 8))

        for t in types_list:
            subset = df_cleaned[df_cleaned['Тип'] == t]
            if subset.empty: continue
            
            offset = y_offsets.get(t, 0.0)
            color = colors.get(t, 'gray')
            
            y_pos = [y_map[loc] + offset for loc in subset['Место']]
            
            ax.scatter(subset['Время'], y_pos, 
                       s=subset['Количество'] * 200, 
                       c=color, label=t, alpha=0.6, edgecolors='black')
            
            for idx, r in subset.iterrows():
                y_coord = y_map[r['Место']] + offset
                ax.annotate(str(r['Количество']), 
                            (r['Время'], y_coord),
                            ha='center', va='center', 
                            fontsize=10, fontweight='bold', color='black')

        ax.set_yticks(range(len(locations_list)))
        ax.set_yticklabels(locations_list)

        plt.title(f'Активность БПЛА ({selected_date})', fontsize=16, fontweight='bold')
        plt.xlabel('Временной промежуток', fontsize=12)
        plt.ylabel('Позиция', fontsize=12)
        plt.xticks(rotation=45)

        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, title='Тип', bbox_to_anchor=(1.01, 1), loc='upper left')

        plt.grid(axis='both', linestyle='--', alpha=0.5)
        plt.tight_layout()

        st.pyplot(fig)

except Exception as e:
    st.error(f"Произошла ошибка при загрузке таблицы: {e}")

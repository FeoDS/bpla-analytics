import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Дашборд БПЛА", layout="wide")
st.title("Аналитика: Активность БПЛА")

# === ВАША ПРЯМАЯ ССЫЛКА НА ФАЙЛ ===
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSI_V0g8qbn-UGALj94aDW3jYFjFvVch7PIklv54n33RsVR9P3mvXGLZBRC-Vi_CEsskTMIdTbsF7Iu/pub?output=xlsx"

@st.cache_resource(ttl=60)
def load_data(url):
    return pd.ExcelFile(url)

try:
    xls = load_data(GOOGLE_SHEET_URL)
    sheet_names = xls.sheet_names
    
    selected_date = st.selectbox("📅 Выберите вкладку (дату):", sheet_names)
    
    df = pd.read_excel(xls, sheet_name=selected_date, header=None)
    raw_data = df.values.tolist()

    if len(raw_data) < 4:
        st.warning("На этой вкладке пока нет данных.")
        st.stop()

    # --- 1. ИЩЕМ СТРОКИ С ШАПКОЙ ---
    locations_row = None
    types_row = None
    data_start_idx = 0

    for i in range(min(15, len(raw_data))):
        row_cells_lower = [str(x).strip().lower() for x in raw_data[i]]
        if 'кассир' in row_cells_lower or 'литейщик' in row_cells_lower:
            locations_row = raw_data[i].copy()
        # Ищем сокращения Я, М, Ф
        if 'я' in row_cells_lower or 'м' in row_cells_lower or 'ф' in row_cells_lower or 'яга' in row_cells_lower:
            types_row = raw_data[i].copy()
            data_start_idx = i + 1

    if locations_row is None or types_row is None:
        st.error("Не удалось найти шапку таблицы. Проверьте, есть ли позывной 'Кассир' и типы 'Я', 'М', 'Ф'.")
        st.stop()

    # --- 2. РАСПРЕДЕЛЯЕМ ПОЗЫВНЫЕ (Заполняем объединенные ячейки) ---
    current_loc = "Неизвестно"
    for i in range(len(locations_row)):
        val = str(locations_row[i]).strip()
        val_lower = val.lower()
        if val and val_lower not in ['nan', 'none', '', '[пусто]', 'точка', 'итого', 'время']:
            current_loc = val
        locations_row[i] = current_loc

    # --- 3. ПАРСИНГ ЦИФР И ПРИВЯЗКА ЦВЕТОВ ---
    parsed_data = []
    for row_idx in range(data_start_idx, len(raw_data)):
        row = raw_data[row_idx]
        time_val = str(row[0]).strip()
        
        if time_val.lower() in ['nan', 'none', '', '[пусто]', 'итого']:
            continue

        for col_idx in range(1, len(row)): 
            if col_idx >= len(locations_row) or col_idx >= len(types_row):
                continue
                
            loc = locations_row[col_idx]
            typ_raw = str(types_row[col_idx]).strip().lower()
            
            # Распознаем новые сокращения из таблицы
            if typ_raw in ['я', 'яга']: typ = 'Яга'
            elif typ_raw in ['м', 'мавик']: typ = 'Мавик'
            elif typ_raw in ['ф', 'фпв']: typ = 'ФПВ'
            elif typ_raw in ['к', 'крыло']: typ = 'Крыло'
            else: continue # Пропускаем столбцы без типов (например, "Итого")

            val = str(row[col_idx]).strip()
            if val.lower() not in ['nan', 'none', '', '[пусто]']:
                clean_val = ''.join(filter(str.isdigit, val))
                if clean_val:
                    parsed_data.append({
                        'Время': time_val,
                        'Место': loc,
                        'Тип': typ,
                        'Количество': int(clean_val)
                    })

    df_cleaned = pd.DataFrame(parsed_data, columns=['Время', 'Место', 'Тип', 'Количество'])

    # --- 4. ОТРИСОВКА ГРАФИКА ---
    if len(df_cleaned) == 0:
        st.info("В выбранный день активность не зафиксирована.")
    else:
        st.success(f"Общее количество зафиксированных меток: **{df_cleaned['Количество'].sum()}**")
        
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

        # Собираем список позывных строго по порядку из шапки таблицы
        locations_list = []
        for loc in locations_row:
            if loc not in locations_list and loc.lower() not in ['nan', 'none', 'неизвестно', 'точка', 'итого', 'время']:
                locations_list.append(loc)
                
        y_map = {loc: i for i, loc in enumerate(locations_list)}
        
        # Назначаем отступы и цвета
        y_offsets = {'Яга': -0.2, 'Мавик': 0.0, 'ФПВ': 0.2, 'Крыло': 0.4}
        colors = {'Яга': 'red', 'Мавик': 'blue', 'ФПВ': 'green', 'Крыло': 'purple'}

        fig, ax = plt.subplots(figsize=(14, max(8, len(locations_list) * 0.8)))

        types_list = df_cleaned['Тип'].unique().tolist()
        
        for t in types_list:
            subset = df_cleaned[df_cleaned['Тип'] == t]
            if subset.empty: continue
            
            offset = y_offsets.get(t, 0.0)
            color = colors.get(t, 'gray')
            
            y_pos = []
            for loc in subset['Место']:
                y_pos.append(y_map.get(loc, 0) + offset)
            
            ax.scatter(subset['Время'], y_pos, 
                       s=subset['Количество'] * 200, 
                       c=color, label=t, alpha=0.6, edgecolors='black')
            
            for idx, r in subset.iterrows():
                loc = r['Место']
                if loc in y_map:
                    y_coord = y_map[loc] + offset
                    ax.annotate(str(r['Количество']), 
                                (r['Время'], y_coord),
                                ha='center', va='center', 
                                fontsize=10, fontweight='bold', color='black')

        ax.set_yticks(range(len(locations_list)))
        ax.set_yticklabels(locations_list)
        ax.invert_yaxis() # Переворачиваем, чтобы Кассир был на самом верху

        plt.title(f'Активность БПЛА ({selected_date})', fontsize=16, fontweight='bold')
        plt.xlabel('Временной промежуток', fontsize=12)
        plt.ylabel('Позывной (Точка)', fontsize=12)
        plt.xticks(rotation=45)

        handles, labels = ax.get_legend_handles_labels()
        plt.legend(handles, labels, title='Тип БПЛА', bbox_to_anchor=(1.01, 1), loc='upper left')

        plt.grid(axis='both', linestyle='--', alpha=0.5)
        plt.tight_layout()

        st.pyplot(fig)

except Exception as e:
    st.error(f"Произошла ошибка при загрузке: {e}")

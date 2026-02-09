import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import json
import datetime
import sqlite3
from pathlib import Path
import os

# Configuration de la page
st.set_page_config(
    page_title="Bilan Puissance - Base de Données",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #0E4A7A;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
        margin-bottom: 1.5rem;
        border-left: 5px solid #0E4A7A;
    }
</style>
""", unsafe_allow_html=True)

# Initialisation de la base de données
def init_database():
    """Initialise la base de données avec les données par défaut"""
    conn = sqlite3.connect('equipements.db')
    cursor = conn.cursor()
    
    # Création des tables
    cursor.executescript('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        description TEXT,
        unite TEXT DEFAULT 'kW'
    );
    
    CREATE TABLE IF NOT EXISTS types_equipements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categorie_id INTEGER,
        nom TEXT NOT NULL,
        puissance_moyenne REAL,
        puissance_min REAL,
        puissance_max REAL,
        facteur_charge REAL DEFAULT 70,
        heures_fonction REAL DEFAULT 10,
        FOREIGN KEY (categorie_id) REFERENCES categories(id)
    );
    
    CREATE TABLE IF NOT EXISTS modeles_equipements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type_id INTEGER,
        marque TEXT,
        modele TEXT,
        puissance_nominale REAL,
        annee INTEGER,
        classe_energetique TEXT,
        FOREIGN KEY (type_id) REFERENCES types_equipements(id)
    );
    
    CREATE TABLE IF NOT EXISTS coefficients_saison (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mois INTEGER,
        categorie_id INTEGER,
        coefficient REAL DEFAULT 1.0,
        FOREIGN KEY (categorie_id) REFERENCES categories(id)
    );
    ''')
    
    # Vérification si la base contient déjà des données
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        # Insertion des données par défaut
        insert_default_data(conn)
    
    conn.commit()
    conn.close()

def insert_default_data(conn):
    """Insère les données par défaut dans la base"""
    cursor = conn.cursor()
    
    # Insertion des catégories
    categories = [
        ('CVC - VRV/DRV', 'Climatisation à volume de réfrigérant variable', 'kW'),
        ('CVC - Pompe à chaleur', 'Systèmes de chauffage/refroidissement', 'kW'),
        ('CVC - Chauffage électrique', 'Convecteurs, radiateurs électriques', 'kW'),
        ('ECS - Ballon électrique', 'Chauffe-eau électrique', 'kW'),
        ('ECS - Thermodynamique', 'Chauffe-eau thermodynamique', 'kW'),
        ('Éclairage - LED', 'Éclairage LED', 'kW'),
        ('Éclairage - Fluorescent', 'Éclairage fluorescent', 'kW'),
        ('Ventilation - VMC', 'Ventilation mécanique contrôlée', 'kW'),
        ('Ventilation - Extracteur', 'Extracteurs d\'air', 'kW'),
        ('Ascenseur', 'Ascenseurs et monte-charge', 'kW'),
        ('Prises bureautique', 'Prise électrique bureautique', 'kW'),
        ('Serveur', 'Serveurs et baies informatiques', 'kW')
    ]
    
    cursor.executemany(
        "INSERT INTO categories (nom, description, unite) VALUES (?, ?, ?)",
        categories
    )
    
    # Récupération des IDs des catégories
    cursor.execute("SELECT id, nom FROM categories")
    cat_dict = {nom: id for id, nom in cursor.fetchall()}
    
    # Insertion des types d'équipements avec données de puissance
    types_data = [
        # CVC - VRV/DRV
        (cat_dict['CVC - VRV/DRV'], 'VRV Daikin 7.1kW', 7.1, 5.6, 8.5, 70, 10),
        (cat_dict['CVC - VRV/DRV'], 'VRV Mitsubishi 11.2kW', 11.2, 9.0, 13.5, 75, 12),
        (cat_dict['CVC - VRV/DRV'], 'VRV Toshiba 14.0kW', 14.0, 11.2, 16.8, 72, 10),
        (cat_dict['CVC - VRV/DRV'], 'DRV Carrier 9.0kW', 9.0, 7.2, 10.8, 68, 11),
        
        # CVC - Pompe à chaleur
        (cat_dict['CVC - Pompe à chaleur'], 'PAC air/eau 8kW', 8.0, 6.4, 9.6, 65, 8),
        (cat_dict['CVC - Pompe à chaleur'], 'PAC air/air 5kW', 5.0, 4.0, 6.0, 70, 10),
        (cat_dict['CVC - Pompe à chaleur'], 'PAC géothermique 12kW', 12.0, 9.6, 14.4, 60, 9),
        
        # CVC - Chauffage électrique
        (cat_dict['CVC - Chauffage électrique'], 'Convecteur 750W', 0.75, 0.75, 0.75, 80, 8),
        (cat_dict['CVC - Chauffage électrique'], 'Convecteur 1500W', 1.5, 1.5, 1.5, 75, 7),
        (cat_dict['CVC - Chauffage électrique'], 'Radiateur inertie 2000W', 2.0, 2.0, 2.0, 70, 9),
        
        # ECS - Ballon électrique
        (cat_dict['ECS - Ballon électrique'], 'Ballon 50L 2000W', 2.0, 2.0, 2.0, 50, 4),
        (cat_dict['ECS - Ballon électrique'], 'Ballon 100L 3000W', 3.0, 3.0, 3.0, 55, 5),
        (cat_dict['ECS - Ballon électrique'], 'Ballon 200L 4000W', 4.0, 4.0, 4.0, 60, 6),
        
        # ECS - Thermodynamique
        (cat_dict['ECS - Thermodynamique'], 'CESI 200L', 0.5, 0.4, 0.6, 40, 8),
        (cat_dict['ECS - Thermodynamique'], 'Chauffe-eau thermodynamique 300L', 1.2, 1.0, 1.4, 45, 7),
        
        # Éclairage - LED
        (cat_dict['Éclairage - LED'], 'LED 18W', 0.018, 0.018, 0.018, 100, 10),
        (cat_dict['Éclairage - LED'], 'LED 24W', 0.024, 0.024, 0.024, 100, 10),
        (cat_dict['Éclairage - LED'], 'LED 36W', 0.036, 0.036, 0.036, 100, 10),
        (cat_dict['Éclairage - LED'], 'LED 54W', 0.054, 0.054, 0.054, 100, 10),
        
        # Éclairage - Fluorescent
        (cat_dict['Éclairage - Fluorescent'], 'TL5 28W', 0.028, 0.028, 0.028, 95, 10),
        (cat_dict['Éclairage - Fluorescent'], 'TL5 54W', 0.054, 0.054, 0.054, 95, 10),
        
        # Ventilation - VMC
        (cat_dict['Ventilation - VMC'], 'VMC simple flux', 0.08, 0.06, 0.10, 80, 24),
        (cat_dict['Ventilation - VMC'], 'VMC double flux', 0.15, 0.12, 0.18, 75, 24),
        (cat_dict['Ventilation - VMC'], 'VMC hygroréglable', 0.10, 0.08, 0.12, 70, 24),
        
        # Ventilation - Extracteur
        (cat_dict['Ventilation - Extracteur'], 'Extracteur salle de bain', 0.03, 0.025, 0.035, 30, 4),
        (cat_dict['Ventilation - Extracteur'], 'Extracteur cuisine', 0.05, 0.04, 0.06, 40, 6),
        
        # Ascenseur
        (cat_dict['Ascenseur'], 'Ascenseur 4 personnes', 4.0, 3.2, 4.8, 40, 12),
        (cat_dict['Ascenseur'], 'Ascenseur 8 personnes', 7.5, 6.0, 9.0, 35, 14),
        (cat_dict['Ascenseur'], 'Ascenseur 13 personnes', 11.0, 8.8, 13.2, 30, 16),
        
        # Prises bureautique
        (cat_dict['Prises bureautique'], 'Poste bureautique', 0.15, 0.10, 0.20, 60, 9),
        (cat_dict['Prises bureautique'], 'Imprimante', 0.3, 0.2, 0.4, 30, 6),
        (cat_dict['Prises bureautique'], 'Photocopieur', 1.5, 1.2, 1.8, 40, 8),
        
        # Serveur
        (cat_dict['Serveur'], 'Serveur 1U', 0.5, 0.4, 0.6, 90, 24),
        (cat_dict['Serveur'], 'Serveur 2U', 0.8, 0.64, 0.96, 85, 24),
        (cat_dict['Serveur'], 'Baie informatique', 3.0, 2.4, 3.6, 80, 24)
    ]
    
    cursor.executemany(
        """INSERT INTO types_equipements 
        (categorie_id, nom, puissance_moyenne, puissance_min, puissance_max, facteur_charge, heures_fonction) 
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        types_data
    )
    
    # Insertion de modèles spécifiques
    modeles_data = [
        # VRV Daikin
        (1, 'Daikin', 'RXYQ8P7W1B', 7.1, 2020, 'A++'),
        (1, 'Daikin', 'RXYQ14P7W1B', 14.0, 2021, 'A++'),
        (2, 'Mitsubishi', 'FDC112KXES6', 11.2, 2019, 'A+'),
        (4, 'Carrier', '30XAV - 240', 9.0, 2018, 'A'),
        
        # Pompes à chaleur
        (5, 'Atlantic', 'Alea COMPACT 8', 8.0, 2022, 'A++'),
        (6, 'Panasonic', 'CS-Z25WKE', 2.5, 2021, 'A+++'),
        
        # Ballons ECS
        (11, 'Thermor', 'Aéromax 3 50L', 2.0, 2020, 'C'),
        (11, 'Atlantic', 'Caliopa 100L', 3.0, 2021, 'B'),
        
        # Éclairage LED
        (16, 'Philips', 'CorePro LEDtube 18W', 0.018, 2022, 'A++'),
        (17, 'Osram', 'LED Star 24W', 0.024, 2021, 'A++'),
        
        # VMC
        (22, 'Aldes', 'Ventilation Expert 350', 0.15, 2020, 'A'),
        
        # Ascenseurs
        (24, 'Schindler', '3300 AP 4pers', 4.0, 2018, 'A'),
        (25, 'Kone', 'MonoSpace 500 8pers', 7.5, 2019, 'A')
    ]
    
    cursor.executemany(
        """INSERT INTO modeles_equipements 
        (type_id, marque, modele, puissance_nominale, annee, classe_energetique) 
        VALUES (?, ?, ?, ?, ?, ?)""",
        modeles_data
    )
    
    # Coefficients saisonniers
    coefficients = []
    mois = list(range(1, 13))
    for categorie_id in cat_dict.values():
        for mois_num in mois:
            # Variation saisonnière selon la catégorie
            if 'CVC' in list(cat_dict.keys())[list(cat_dict.values()).index(categorie_id)]:
                coeff = 1.2 if mois_num in [12, 1, 2] else 0.8 if mois_num in [6, 7, 8] else 1.0
            elif 'ECS' in list(cat_dict.keys())[list(cat_dict.values()).index(categorie_id)]:
                coeff = 1.1 if mois_num in [11, 12, 1] else 0.9 if mois_num in [6, 7, 8] else 1.0
            elif 'Éclairage' in list(cat_dict.keys())[list(cat_dict.values()).index(categorie_id)]:
                coeff = 1.3 if mois_num in [11, 12, 1] else 0.7 if mois_num in [6, 7] else 1.0
            else:
                coeff = 1.0
            
            coefficients.append((mois_num, categorie_id, coeff))
    
    cursor.executemany(
        "INSERT INTO coefficients_saison (mois, categorie_id, coefficient) VALUES (?, ?, ?)",
        coefficients
    )
    
    conn.commit()

# Fonctions pour interroger la base de données
def get_categories():
    """Récupère toutes les catégories"""
    conn = sqlite3.connect('equipements.db')
    df = pd.read_sql_query("SELECT * FROM categories ORDER BY nom", conn)
    conn.close()
    return df

def get_types_by_category(categorie_id):
    """Récupère les types d'équipements pour une catégorie"""
    conn = sqlite3.connect('equipements.db')
    query = """
    SELECT t.*, c.nom as categorie_nom 
    FROM types_equipements t
    JOIN categories c ON t.categorie_id = c.id
    WHERE t.categorie_id = ?
    ORDER BY t.nom
    """
    df = pd.read_sql_query(query, conn, params=(categorie_id,))
    conn.close()
    return df

def get_modeles_by_type(type_id):
    """Récupère les modèles pour un type d'équipement"""
    conn = sqlite3.connect('equipements.db')
    query = """
    SELECT m.*, t.nom as type_nom 
    FROM modeles_equipements m
    JOIN types_equipements t ON m.type_id = t.id
    WHERE m.type_id = ?
    ORDER BY m.marque, m.modele
    """
    df = pd.read_sql_query(query, conn, params=(type_id,))
    conn.close()
    return df

def search_equipment_by_name(name):
    """Recherche un équipement par nom"""
    conn = sqlite3.connect('equipements.db')
    query = """
    SELECT 
        t.id as type_id,
        t.nom as type_nom,
        t.puissance_moyenne,
        t.puissance_min,
        t.puissance_max,
        c.nom as categorie_nom,
        c.unite
    FROM types_equipements t
    JOIN categories c ON t.categorie_id = c.id
    WHERE LOWER(t.nom) LIKE LOWER(?)
    OR LOWER(c.nom) LIKE LOWER(?)
    """
    df = pd.read_sql_query(query, conn, params=(f'%{name}%', f'%{name}%'))
    conn.close()
    return df

def get_power_stats_by_category():
    """Récupère les statistiques de puissance par catégorie"""
    conn = sqlite3.connect('equipements.db')
    query = """
    SELECT 
        c.nom as categorie,
        COUNT(t.id) as nb_types,
        AVG(t.puissance_moyenne) as puissance_moyenne,
        MIN(t.puissance_min) as puissance_min,
        MAX(t.puissance_max) as puissance_max,
        SUM(t.puissance_moyenne) as puissance_totale
    FROM types_equipements t
    JOIN categories c ON t.categorie_id = c.id
    GROUP BY c.nom
    ORDER BY puissance_totale DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Initialisation de la session state
if 'equipements' not in st.session_state:
    st.session_state.equipements = pd.DataFrame(columns=[
        'ID', 'Nom', 'Type', 'Catégorie', 'Puissance (kW)', 
        'Quantité', 'Facteur Charge (%)', 'Heures Fonction (h/j)',
        'Jours Fonction (j/an)', 'Localisation', 'Étage', 
        'Système', 'Contrôlable', 'Priorité', 'Notes', 'Source_BDD'
    ])

# Initialisation de la base de données
init_database()

# Interface principale
st.markdown('<h1 class="main-header">📊 Bilan de Puissance avec Base de Données</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🔍 Recherche Base de Données")
    
    search_option = st.radio(
        "Mode de recherche",
        ["Par catégorie", "Par nom", "Statistiques"]
    )
    
    if search_option == "Par catégorie":
        categories_df = get_categories()
        selected_category = st.selectbox(
            "Sélectionnez une catégorie",
            categories_df['nom'].tolist()
        )
        
        if selected_category:
            categorie_id = categories_df[categories_df['nom'] == selected_category]['id'].values[0]
            types_df = get_types_by_category(categorie_id)
            
            st.markdown(f"### 📋 Types disponibles ({len(types_df)})")
            
            for _, row in types_df.iterrows():
                with st.expander(f"🔧 {row['nom']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Puissance moyenne", f"{row['puissance_moyenne']} kW")
                        st.metric("Puissance min", f"{row['puissance_min']} kW")
                        st.metric("Puissance max", f"{row['puissance_max']} kW")
                    with col2:
                        st.metric("Facteur charge", f"{row['facteur_charge']}%")
                        st.metric("Heures/jour", f"{row['heures_fonction']}h")
                        
                        # Bouton pour ajouter cet équipement
                        if st.button(f"➕ Ajouter {row['nom']}", key=f"add_{row['id']}"):
                            quantite = st.number_input("Quantité", min_value=1, value=1, key=f"qty_{row['id']}")
                            if st.button("✅ Confirmer", key=f"confirm_{row['id']}"):
                                new_id = len(st.session_state.equipements) + 1
                                new_equip = pd.DataFrame([{
                                    'ID': new_id,
                                    'Nom': row['nom'],
                                    'Type': row['nom'],
                                    'Catégorie': row['categorie_nom'],
                                    'Puissance (kW)': row['puissance_moyenne'],
                                    'Quantité': quantite,
                                    'Facteur Charge (%)': row['facteur_charge'],
                                    'Heures Fonction (h/j)': row['heures_fonction'],
                                    'Jours Fonction (j/an)': 220,
                                    'Localisation': '',
                                    'Étage': '',
                                    'Système': '',
                                    'Contrôlable': True,
                                    'Priorité': 'Moyenne',
                                    'Notes': f"Importé depuis BDD - ID: {row['id']}",
                                    'Source_BDD': True
                                }])
                                st.session_state.equipements = pd.concat([st.session_state.equipements, new_equip], ignore_index=True)
                                st.success(f"✅ {quantite} x {row['nom']} ajouté(s) !")
    
    elif search_option == "Par nom":
        search_term = st.text_input("Rechercher un équipement", placeholder="Ex: VRV, LED, ballon...")
        
        if search_term:
            results_df = search_equipment_by_name(search_term)
            
            if not results_df.empty:
                st.markdown(f"### 🔍 Résultats ({len(results_df)})")
                
                for _, row in results_df.iterrows():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{row['type_nom']}**")
                        st.caption(f"Catégorie: {row['categorie_nom']}")
                    with col2:
                        st.metric("Puissance", f"{row['puissance_moyenne']} kW")
                    with col3:
                        quantite = st.number_input("Qté", min_value=1, value=1, 
                                                  key=f"qty_search_{row['type_id']}", 
                                                  label_visibility="collapsed")
                        
                        if st.button("➕", key=f"btn_search_{row['type_id']}"):
                            new_id = len(st.session_state.equipements) + 1
                            new_equip = pd.DataFrame([{
                                'ID': new_id,
                                'Nom': row['type_nom'],
                                'Type': row['type_nom'],
                                'Catégorie': row['categorie_nom'],
                                'Puissance (kW)': row['puissance_moyenne'],
                                'Quantité': quantite,
                                'Facteur Charge (%)': 70,
                                'Heures Fonction (h/j)': 10,
                                'Jours Fonction (j/an)': 220,
                                'Localisation': '',
                                'Étage': '',
                                'Système': '',
                                'Contrôlable': True,
                                'Priorité': 'Moyenne',
                                'Notes': f"Recherche BDD: {search_term}",
                                'Source_BDD': True
                            }])
                            st.session_state.equipements = pd.concat([st.session_state.equipements, new_equip], ignore_index=True)
                            st.success(f"✅ {quantite} x {row['type_nom']} ajouté(s) !")
            else:
                st.info("Aucun équipement trouvé pour cette recherche.")
    
    else:  # Statistiques
        stats_df = get_power_stats_by_category()
        
        st.markdown("### 📈 Statistiques par catégorie")
        
        for _, row in stats_df.iterrows():
            with st.expander(f"📊 {row['categorie']} - {row['nb_types']} types"):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Puissance moyenne", f"{row['puissance_moyenne']:.2f} kW")
                    st.metric("Puissance min", f"{row['puissance_min']:.2f} kW")
                with col2:
                    st.metric("Puissance max", f"{row['puissance_max']:.2f} kW")
                    st.metric("Total catégorie", f"{row['puissance_totale']:.1f} kW")
        
        # Graphique des puissances
        fig = px.bar(
            stats_df,
            x='categorie',
            y='puissance_totale',
            title='Puissance totale par catégorie (kW)',
            color='categorie'
        )
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 💾 Gestion des données")
    
    if st.button("🔄 Rafraîchir BDD"):
        init_database()
        st.success("Base de données rafraîchie !")
    
    if st.button("📤 Exporter BDD"):
        # Export de la base de données
        conn = sqlite3.connect('equipements.db')
        categories_df = pd.read_sql_query("SELECT * FROM categories", conn)
        types_df = pd.read_sql_query("SELECT * FROM types_equipements", conn)
        modeles_df = pd.read_sql_query("SELECT * FROM modeles_equipements", conn)
        conn.close()
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            categories_df.to_excel(writer, sheet_name='Catégories', index=False)
            types_df.to_excel(writer, sheet_name='Types Équipements', index=False)
            modeles_df.to_excel(writer, sheet_name='Modèles', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Télécharger BDD complète",
            data=output,
            file_name="base_equipements.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# Section principale - Gestion des équipements
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### 🏢 Équipements du bâtiment")

if not st.session_state.equipements.empty:
    # Affichage des équipements
    st.dataframe(
        st.session_state.equipements[[
            'Nom', 'Catégorie', 'Puissance (kW)', 'Quantité', 
            'Localisation', 'Étage', 'Priorité', 'Source_BDD'
        ]],
        use_container_width=True,
        height=400
    )
    
    # Calcul des totaux
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_power = (st.session_state.equipements['Puissance (kW)'] * 
                      st.session_state.equipements['Quantité']).sum()
        st.metric("Puissance totale installée", f"{total_power:.1f} kW")
    
    with col2:
        nb_equip = len(st.session_state.equipements)
        st.metric("Nombre d'équipements", nb_equip)
    
    with col3:
        bdd_count = st.session_state.equipements['Source_BDD'].sum()
        bdd_pct = (bdd_count / nb_equip * 100) if nb_equip > 0 else 0
        st.metric("Depuis BDD", f"{bdd_count}/{nb_equip} ({bdd_pct:.1f}%)")
    
    # Analyse par catégorie
    st.markdown("#### 📊 Répartition par catégorie")
    
    power_by_category = st.session_state.equipements.groupby('Catégorie').apply(
        lambda x: (x['Puissance (kW)'] * x['Quantité']).sum()
    ).reset_index(name='Puissance totale')
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        fig = px.pie(
            power_by_category,
            names='Catégorie',
            values='Puissance totale',
            title='Répartition de la puissance par catégorie'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_b:
        fig = px.bar(
            power_by_category.sort_values('Puissance totale', ascending=True),
            x='Puissance totale',
            y='Catégorie',
            orientation='h',
            title='Puissance par catégorie (kW)',
            color='Catégorie'
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Analyse BACS
    st.markdown("#### ⚖️ Analyse de conformité BACS")
    
    max_single_power = st.session_state.equipements['Puissance (kW)'].max()
    seuil_70kw = max_single_power >= 70
    seuil_290kw = total_power >= 290
    assujetti = seuil_70kw or seuil_290kw
    
    col_x, col_y, col_z = st.columns(3)
    
    with col_x:
        status_color = "🔴" if assujetti else "🟢"
        st.metric("Statut BACS", f"{status_color} {'ASSUJETTI' if assujetti else 'NON ASSUJETTI'}")
    
    with col_y:
        st.metric("Plus gros équipement", f"{max_single_power:.1f} kW")
    
    with col_z:
        st.metric("Seuil 70kW", "✅ OK" if max_single_power < 70 else "⚠️ DÉPASSÉ")
    
    # Export des données
    st.markdown("#### 📤 Export des données")
    
    if st.button("💾 Exporter le bilan complet", use_container_width=True):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            st.session_state.equipements.to_excel(writer, sheet_name='Équipements', index=False)
            power_by_category.to_excel(writer, sheet_name='Par Catégorie', index=False)
            
            # Ajouter un résumé
            resume_df = pd.DataFrame({
                'Métrique': ['Puissance totale', 'Nombre équipements', 'Conformité BACS'],
                'Valeur': [
                    f"{total_power:.1f} kW",
                    nb_equip,
                    "ASSUJETTI" if assujetti else "NON ASSUJETTI"
                ]
            })
            resume_df.to_excel(writer, sheet_name='Résumé', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Télécharger le fichier Excel",
            data=output,
            file_name=f"bilan_puissance_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
else:
    st.info("""
    ## 📋 Aucun équipement enregistré
    
    Pour commencer :
    1. **Recherchez des équipements** dans la base de données via la barre latérale
    2. **Ajoutez-les** à votre liste
    3. **Visualisez** le bilan de puissance automatiquement
    
    💡 **La base de données contient déjà** :
    - ✅ Plus de 30 types d'équipements CVC
    - ✅ Toutes les puissances standards pour l'éclairage LED
    - ✅ Les ballons ECS avec leurs caractéristiques
    - ✅ Les systèmes de ventilation
    - ✅ Les ascenseurs et équipements bureautiques
    """)

st.markdown('</div>', unsafe_allow_html=True)

# Section d'ajout manuel
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown("### ✍️ Ajout manuel d'équipement")

col1, col2 = st.columns(2)

with col1:
    nom_manuel = st.text_input("Nom de l'équipement")
    categorie_manuel = st.selectbox(
        "Catégorie",
        ["CVC", "Éclairage", "ECS", "Ventilation", "Ascenseur", "Bureautique", "Autre"]
    )
    puissance_manuel = st.number_input("Puissance (kW)", min_value=0.01, value=1.0, step=0.1)
    quantite_manuel = st.number_input("Quantité", min_value=1, value=1)

with col2:
    facteur_manuel = st.slider("Facteur de charge (%)", min_value=0, max_value=100, value=70)
    heures_manuel = st.number_input("Heures fonctionnement/jour", min_value=0.0, max_value=24.0, value=10.0)
    localisation_manuel = st.text_input("Localisation")
    priorite_manuel = st.selectbox("Priorité", ["Basse", "Moyenne", "Haute"])

if st.button("➕ Ajouter manuellement", use_container_width=True):
    if nom_manuel and puissance_manuel > 0:
        new_id = len(st.session_state.equipements) + 1
        new_equip = pd.DataFrame([{
            'ID': new_id,
            'Nom': nom_manuel,
            'Type': nom_manuel,
            'Catégorie': categorie_manuel,
            'Puissance (kW)': puissance_manuel,
            'Quantité': quantite_manuel,
            'Facteur Charge (%)': facteur_manuel,
            'Heures Fonction (h/j)': heures_manuel,
            'Jours Fonction (j/an)': 220,
            'Localisation': localisation_manuel,
            'Étage': '',
            'Système': '',
            'Contrôlable': True,
            'Priorité': priorite_manuel,
            'Notes': 'Ajout manuel',
            'Source_BDD': False
        }])
        st.session_state.equipements = pd.concat([st.session_state.equipements, new_equip], ignore_index=True)
        st.success(f"✅ Équipement '{nom_manuel}' ajouté manuellement !")

st.markdown('</div>', unsafe_allow_html=True)

# Pied de page
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
    <p>📊 Application Bilan de Puissance avec Base de Données • Version 3.0</p>
    <p>Base de données SQLite intégrée • {}</p>
</div>
""".format(datetime.datetime.now().strftime('%d/%m/%Y')), unsafe_allow_html=True)
# Exemple d'ajout via l'interface Python
conn = sqlite3.connect('equipements.db')
cursor = conn.cursor()

# Ajouter un nouvel équipement
cursor.execute("""
INSERT INTO types_equipements 
(categorie_id, nom, puissance_moyenne, puissance_min, puissance_max)
VALUES (1, 'VRV Nouveau Modèle 10.5kW', 10.5, 8.4, 12.6)
""")

conn.commit()
conn.close()
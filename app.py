import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import tempfile
import os
from google import genai
from google.genai import types
from PIL import Image
import io
import time
from pydantic import BaseModel, Field
from typing import Optional

st.set_page_config(page_title="📣 Comunica IME", layout="wide")

# Configurações do Firebase
PROJECT_ID = "site-departamento"
FIREBASE_API_KEY = st.secrets.get("FIREBASE_API_KEY", "")
GEMINI_API_KEY_SECRET = st.secrets.get("GEMINI_API_KEY", "")
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents"
# Ajustado para o formato do projeto do usuário: site-departamento.firebasestorage.app
STORAGE_BUCKET = f"{PROJECT_ID}.firebasestorage.app"

def upload_to_storage(file_bytes, file_name, mime_type):
    """Sobe arquivo para o Firebase Storage e retorna o link de acesso."""
    try:
        import urllib.parse
        # Organiza por data no Storage
        data_pasta = datetime.now().strftime("%Y-%m-%d")
        caminho_storage = f"solicitacoes/{data_pasta}/{file_name}"
        esc_name = urllib.parse.quote(caminho_storage, safe="")
        
        # O parâmetro uploadType=media é crucial para o Firebase Storage REST API
        url = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o?uploadType=media&name={esc_name}"
        headers = {"Content-Type": mime_type}
        
        resp = requests.post(url, data=file_bytes, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            # O Firebase Storage via REST geralmente retorna o token em downloadTokens
            token = data.get("downloadTokens", "")
            
            # Caso não venha direto (depende da versão da API), tentamos metadados
            if not token and "metadata" in data:
                token = data.get("metadata", {}).get("firebaseStorageDownloadTokens", "")
            
            # Se ainda não tiver token, o arquivo subiu mas o link público pode falhar
            # Em regras 'if true', alt=media pode funcionar sem token em alguns casos, 
            # mas o token é o padrão Firebase.
            final_url = f"https://firebasestorage.googleapis.com/v0/b/{STORAGE_BUCKET}/o/{esc_name}?alt=media"
            if token:
                final_url += f"&token={token}"
            
            return final_url
        else:
            st.error(f"Erro no Upload ({file_name}): {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        st.error(f"Falha técnica no upload: {str(e)}")
        return None

def adicionar_documento(colecao, dados):
    url = f"{BASE_URL}/{colecao}?key={FIREBASE_API_KEY}"
    
    fields = {}
    for key, value in dados.items():
        if isinstance(value, bool): fields[key] = {"booleanValue": value}
        elif isinstance(value, str): fields[key] = {"stringValue": value}
        elif isinstance(value, int): fields[key] = {"integerValue": str(value)}
        elif isinstance(value, list):
            fields[key] = {"arrayValue": {"values": [{"stringValue": str(v)} for v in value]}}
        elif hasattr(value, "isoformat"): fields[key] = {"timestampValue": value.isoformat() + "Z"}
            
    payload = {"fields": fields}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return True, "Sucesso"
        else:
            return False, f"Status {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def listar_documentos(colecao):
    url = f"{BASE_URL}/{colecao}?key={FIREBASE_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        documents = data.get("documents", [])
        lista_formatada = []
        for doc in documents:
            fields = doc.get("fields", {})
            item = {"id": doc["name"].split("/")[-1]}
            for key, val in fields.items():
                if "stringValue" in val: item[key] = val["stringValue"]
                elif "integerValue" in val: item[key] = int(val["integerValue"])
                elif "booleanValue" in val: item[key] = val["booleanValue"]
                elif "timestampValue" in val: item[key] = val["timestampValue"]
                elif "arrayValue" in val:
                    # Extrai os valores da lista (arrayValue)
                    values = val["arrayValue"].get("values", [])
                    parsed_array = []
                    for v in values:
                        if "stringValue" in v:
                            parsed_array.append(v["stringValue"])
                        elif "mapValue" in v:
                            map_fields = v["mapValue"].get("fields", {})
                            map_dict = {}
                            for mk, mv in map_fields.items():
                                if "stringValue" in mv: map_dict[mk] = mv["stringValue"]
                                elif "doubleValue" in mv: map_dict[mk] = mv["doubleValue"]
                                elif "integerValue" in mv: map_dict[mk] = int(mv["integerValue"])
                                elif "booleanValue" in mv: map_dict[mk] = mv["booleanValue"]
                            parsed_array.append(map_dict)
                    item[key] = parsed_array
            lista_formatada.append(item)
        return lista_formatada
    return []

def atualizar_status_solicitacao(doc_id, novo_status):
    # PATCH para atualizar apenas o campo status
    url = f"{BASE_URL}/solicitacoes/{doc_id}?updateMask.fieldPaths=status&key={FIREBASE_API_KEY}"
    payload = {
        "fields": {
            "status": {"stringValue": novo_status}
        }
    }
    response = requests.patch(url, json=payload)
    return response.status_code == 200

def atualizar_tentativas_ia(doc_id, novo_array):
    """
    Salva o histórico de gerações de IA no Firestore usando mapValues nativos.
    """
    map_values_list = []
    for tentativa in novo_array:
        fields = {}
        for k, v in tentativa.items():
            if isinstance(v, float) or isinstance(v, int):
                fields[k] = {"doubleValue": float(v)}
            else:
                fields[k] = {"stringValue": str(v) if v is not None else ""}
                
        map_values_list.append({"mapValue": {"fields": fields}})
        
    url = f"{BASE_URL}/solicitacoes/{doc_id}?updateMask.fieldPaths=tentativas_ia&key={FIREBASE_API_KEY}"
    payload = {
        "fields": {
            "tentativas_ia": {
                "arrayValue": {
                    "values": map_values_list
                }
            }
        }
    }
    try:
        response = requests.patch(url, json=payload)
        if response.status_code != 200:
            print(f"Erro ao atualizar Firestore (status {response.status_code}): {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Exception ao atualizar tentativas_ia: {e}")
        return False


def page_solicitar_publicacao():
    st.header("📣 Comunica IME")
    st.markdown("""
    **Bem-vindo à Central de Solicitações de Divulgação.** 
    Este canal foi criado para centralizar e organizar todas as demandas de comunicação do IME, 
    garantindo que eventos, editais, defesas e conquistas alcancem nossa comunidade de forma 
    eficiente e profissional através dos nossos canais oficiais.
    """)
    st.divider()

    # Força layout centralizado especificamente para esta página
    st.markdown("""
        <style>
        .block-container {
            max-width: 800px !important;
            padding-top: 2rem;
            padding-bottom: 2rem;
            margin: 0 auto;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Gambiarra para manter seleção obrigatória no segmented_control ---
    if "un_sticky" not in st.session_state: st.session_state.un_sticky = "Depto de Estatística"
    if "ch_sticky" not in st.session_state: st.session_state.ch_sticky = ["Instagram", "Site Oficial"]
    
    # Armazenam o último valor válido para restauração
    if "un_last" not in st.session_state: st.session_state.un_last = "Depto de Estatística"
    if "ch_last" not in st.session_state: st.session_state.ch_last = ["Instagram", "Site Oficial"]

    def sync_un():
        if st.session_state.un_sticky is None: st.session_state.un_sticky = st.session_state.un_last
        else: st.session_state.un_last = st.session_state.un_sticky

    def sync_ch():
        if not st.session_state.ch_sticky: st.session_state.ch_sticky = st.session_state.ch_last
        else: st.session_state.ch_last = st.session_state.ch_sticky
    
    # Listas de Docentes extraídas
    DOCENTES_DEST = [
        "Andrea Prudente", "Carolina Paraíba", "Denise Viola", "Edleide Brito", 
        "Gecynalda Gomes", "Gilberto Sassi", "Giovana Silva", "Helder Zacharias", 
        "Jalmar Carrasco", "Kim Samejima", "Leila Amorim", "Lilia Costa", 
        "Lizandra Fabio", "Marcelo Taddeo", "Maristela Oliveira", "Nívea Silva", 
        "Patrícia Ospina", "Paulo Canas", "Paulo Silva", "Raydonal Ospina", 
        "Ricardo Rocha", "Rodney Fonseca", "Rodrigo Bulhões", "Rosemeire Fiaccone", 
        "Silvia Morais", "Veronica Lima"
    ]
    
    DOCENTES_DMAT = [
        "Ana Lima", "Andreas Brunner", "Antonio Marques", "Augusto Júnior", 
        "Carlos Bahiano", "Cristiana Valente", "David Hill", "Edson Teran", 
        "Eliana Soares", "Elinalva Vasconcelos", "Enaldo Vergasta", "Evandro Santos", 
        "Ezio Costa", "Glória Costa", "Graça Santos", "Isaac Lázaro", 
        "Isamara Alves", "João Fontes", "Jodália Barbosa", "José Andrade", 
        "José Barbosa", "Joseph Yartey", "Leopoldina Menezes", "Luzinalva Amorim", 
        "Mauricio Sicre", "Marcelo Cajueiro", "Márcia Menezes", "Marco Fernandes", 
        "Maria Menezes", "Maria Souza", "Peter Johnson", "Raimundo Torres", 
        "Rita Silva", "Samuel Silva", "Silvia Guimarães", "Thierry Lobão", 
        "Vilton Pinheiro", "Wilton Oliver"
    ]

    unidade = st.segmented_control(
        "Unidade", ["Depto de Estatística", "Depto de Matemática", "IME", "NEX"], 
        selection_mode="single", key="un_sticky", on_change=sync_un
    )
    
    # Lógica de exibição e seleção
    solicitante = None
    postando_como = None
    
    if unidade:
        if unidade == "Depto de Estatística":
            lista_solicitantes = sorted(DOCENTES_DEST)
            opcoes_postando = ["Docente", "Chefe de Departamento", "Colegiado", "Representante do Núcleo de Extensão", "Coordenador de Laboratório", "Outro"]
        elif unidade == "Depto de Matemática":
            lista_solicitantes = sorted(DOCENTES_DMAT)
            opcoes_postando = ["Docente", "Chefe de Departamento", "Colegiado", "Representante do Núcleo de Extensão", "Coordenador de Laboratório", "Outro"]
        elif unidade == "IME":
            lista_solicitantes = sorted(["Ricardo Rocha", "Giovana Silva", "Cristina", "Kleyber"])
            opcoes_postando = ["Diretor do Instituto", "Núcleo de Comunicações", "Técnico Administrativo", "Técnico de Informática", "Outro"]
        elif unidade == "NEX":
            lista_solicitantes = sorted(["Giovana Silva", "Cristina"])
            opcoes_postando = ["Coordenador do NEX", "Membro da Equipe", "Voluntário de Extensão", "Outro"]
            
        colA, colB = st.columns(2)
        with colA:
            solicitante = st.selectbox(
                "Docente / Nome do Solicitante", 
                lista_solicitantes, 
                index=None, 
                placeholder="Selecione o nome...",
            )
        with colB:
            postando_como = st.selectbox(
                "Postando como:", 
                opcoes_postando, 
                index=None, 
                placeholder="Selecione o cargo/papel...",
            )
    


    categorias_demanda = [
        "Ensino (Edital, Monitoria, TCC, Aulas...)",
        "Pesquisa (Defesas, Publicações, Prêmios...)",
        "Extensão (Eventos, Cursos, Projetos Abertos...)",
        "Administrativo / Institucional"
    ]
    tipo_demanda = st.selectbox("Categoria da Solicitação", categorias_demanda)
    
    col_publico, col_arte = st.columns(2)
    with col_publico:
        publico_alvo = st.selectbox(
            "Público-alvo Principal",
            ["Comunidade em Geral (Aberto)", "Apenas Alunos (Graduação/Pós)", "Apenas Docentes e Servidores", "Público Externo"]
        )
    with col_arte:
        st.write("") # Espaçamento para alinhar com o selectbox
        st.write("")
        arte_pronta = st.checkbox("✅ A arte final já está nos anexos (Criar apenas a legenda)")
    
    col_dt1, col_dt2 = st.columns(2)
    
    with col_dt1:
        # Validação de Data de Publicação (Mínimo 24h, Urgência < 48h)
        default_date = (datetime.now() + timedelta(days=7)).replace(minute=0, second=0, microsecond=0)
        data_pub = st.datetime_input(
            "Data pretendida de publicação", 
            value=default_date,
            step=timedelta(hours=1),
            format="DD/MM/YYYY",
            help="Entre 24h e 48h é considerado URGENTE."
        )

    with col_dt2:
         data_evento = st.datetime_input(
            "Data e Hora do Evento (Opcional)", 
            value=None,
            step=timedelta(hours=1),
            format="DD/MM/YYYY",
            help="Se for um evento com horário marcado, insira aqui."
        )
    
    agora = datetime.now()
    diferenca = data_pub - agora
    urgencia = False
    data_valida = True

    if diferenca < timedelta(hours=24):
        st.error("⚠️ O prazo mínimo para solicitações é de **24 horas**. Por favor, escolha um horário posterior.")
        data_valida = False
    elif diferenca < timedelta(hours=48):
        st.warning("🚨 **Atenção**: Esta solicitação será tratada com **URGÊNCIA** (Prazo menor que 48h).")
        urgencia = True

    canais = st.segmented_control(
        "Canais de Divulgação", 
        ["Instagram", "LinkedIn", "Site Oficial", "WhatsApp", "Lista de e-mails dos docentes"],
        selection_mode="multi", key="ch_sticky", on_change=sync_ch
    )

    st.divider()
    st.markdown("### 📎 2. Descrição e Anexos")

    # CSS para aumentar a área de escrita do chat_input
    st.markdown("""
        <style>
        [data-testid="stChatInput"] textarea {
            min-height: 120px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Gerenciamento de estado para armazenar os dados do chat_input antes do envio final
    if "pedido_tmp" not in st.session_state:
        st.session_state.pedido_tmp = None

    with st.container(border=True):
        solicitacao_input = st.chat_input(
            "Descreva detalhadamente a sua solicitação (fornecendo URLs, horários, locais, objetivos e público-alvo pretendido). Utilize o ícone de anexo lateral para incluir materiais adicionais (arquivos PDF, cartazes, imagens ou áudios). Após o preenchimento, confirme o envio nesta barra para habilitar o botão de Finalizar Solicitação, exibido logo abaixo.",
            accept_file="multiple",
            accept_audio=True
        )

    if solicitacao_input:
        st.session_state.pedido_tmp = solicitacao_input

    # Verifica se faltam dados obrigatórios para habilitar o botão de envio
    pode_enviar = bool(solicitante and postando_como and data_valida and st.session_state.pedido_tmp is not None)

    # O botão final fica visível mas desativado enquanto não estiver tudo preenchido
    btn_enviar = st.button("🚀 Finalizar Solicitação e Enviar", type="primary", use_container_width=True, disabled=not pode_enviar)
    
    if btn_enviar:
        with st.status("🚀 Registrando sua solicitação e subindo anexos...", expanded=True) as status:
            descricao_final = st.session_state.pedido_tmp.text or ""
            arquivos = st.session_state.pedido_tmp.files or []
            audio_gravado = st.session_state.pedido_tmp.audio
            
            links_final = []
            
            # Processamento de Arquivos Selecionados
            for f in arquivos:
                status.write(f"📤 Subindo arquivo: {f.name}...")
                url_storage = upload_to_storage(f.getvalue(), f.name, f.type)
                if url_storage:
                    links_final.append(url_storage)
            
            # Processamento de Áudio Gravado
            if audio_gravado:
                status.write("🎤 Subindo áudio gravado...")
                nome_wav = f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                url_audio = upload_to_storage(audio_gravado.getvalue(), nome_wav, "audio/wav")
                if url_audio:
                    links_final.append(url_audio)
            
            # Persistência no Firestore
            dados_solicitacao = {
                "unidade": unidade,
                "solicitante": solicitante,
                "postando_como": postando_como,
                "tipo": tipo_demanda,
                "publico_alvo": publico_alvo,
                "arte_pronta": arte_pronta,
                "data_evento": data_evento, # Pode ser None
                "data_publicacao": data_pub, # Agora enviando como objeto datetime (Timestamp no Firestore)
                "canais": ", ".join(canais),
                "descricao": descricao_final,
                "anexos": links_final,
                "data_solicitacao": datetime.now(), # Agora como datetime.now() local para bater com data_pub
                "status": "Pendente",
                "urgencia": urgencia
            }
            
            sucesso, msg_erro = adicionar_documento("solicitacoes", dados_solicitacao)
            if sucesso:
                st.session_state.pedido_tmp = None  # Limpa do estado o rascunho temporario
                status.update(label="✅ Solicitação registrada com sucesso!", state="complete", expanded=False)
                st.balloons()
                msg_urg = " (Tratada como URGENTE)" if urgencia else ""
                nome_exibicao = solicitante.split(" ")[0]
                st.success(f"💻 Tudo pronto, {nome_exibicao}! Sua demanda{msg_urg} foi enviada.")
                time.sleep(2.5)
                st.rerun()
            else:
                status.update(label=f"❌ Erro ao salvar no banco de dados: {msg_erro}", state="error")

def page_dashboard_solicitacoes():
    st.header("📊 Dashboard de Solicitações")
    st.markdown("Gerenciamento de todas as demandas de comunicação enviadas pelos docentes.")
    
    solicitacoes = listar_documentos("solicitacoes")
    
    if not solicitacoes:
        st.info("Nenhuma solicitação encontrada no banco de dados.")
        return

    # Ordenação: Data de publicação mais próxima primeiro (ascendente)
    solicitacoes.sort(key=lambda x: x.get("data_publicacao", "9999-12-31"))

    def formatar_br(data_val):
        if not data_val: return "N/A"
        try:
            # Caso já seja um objeto datetime (raro via REST, mas possível localmente)
            if isinstance(data_val, datetime):
                return data_val.strftime("%d/%m/%Y %H:%M")
            
            # Limpeza de string para ISO (remove 'T', 'Z', etc)
            ds = str(data_val).replace("T", " ").replace("Z", "").split(".")[0]
            
            # Tenta converter de formatos comuns
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(ds, fmt)
                    return dt.strftime("%d/%m/%Y %H:%M")
                except:
                    continue
            return ds # Fallback se nada funcionar
        except:
            return str(data_val)

    def extrair_nome_arquivo(url):
        """Tenta extrair o nome real do arquivo da URL do Firebase Storage."""
        try:
            import urllib.parse
            path_part = url.split('/o/')[-1].split('?')[0]
            decoded_path = urllib.parse.unquote(path_part)
            return decoded_path.split('/')[-1]
        except:
            return "Arquivo"

    # Estilização CSS personalizada para os radio buttons
    st.markdown("""
        <style>
        /* Esconder o círculo padrão do radio */
        div[role="radiogroup"] > label > div:first-child {
            display: none;
        }
        /* Estilizar o label inteiro como um card moderno */
        div[role="radiogroup"] > label {
            border: 1px solid rgba(250, 250, 250, 0.2);
            border-radius: 8px;
            padding: 15px 15px;
            margin-bottom: 8px;
            transition: all 0.2s ease-in-out;
            background-color: rgba(255, 255, 255, 0.02);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            cursor: pointer;
            width: 100%;
        }
        /* Efeito de hover */
        div[role="radiogroup"] > label:hover {
            border-color: #007bff;
            background-color: rgba(0, 123, 255, 0.05);
            transform: translateY(-1px);
        }
        /* Estilização para o item selecionado (usando :has do CSS4) */
        div[role="radiogroup"] > label:has(input:checked) {
            border-color: #007bff;
            background-color: rgba(0, 123, 255, 0.1);
            box-shadow: 0 4px 10px rgba(0, 123, 255, 0.15);
        }
        div[role="radiogroup"] > label:has(input:checked) div {
            font-weight: 600;
            color: #007bff !important;
        }
        </style>
    """, unsafe_allow_html=True)

    col_list, col_details = st.columns([1, 2])
    
    with col_list:
        with st.container(border=True):
            st.subheader("📋 Lista de Solicitações")
            
            # Cria as opções para o Radio button
            opcoes_radio = []
            dict_sols = {}
            for sol in solicitacoes:
                status = sol.get("status", "Pendente")
                urgente = sol.get("urgencia", False)
                header_prefix = "🚨 " if urgente and status == "Pendente" else ""
                status_icon = "⏳" if status == "Pendente" else ("✅" if status == "Feito" else "❌")
                
                tipo = sol.get('tipo', 'Solicitação').upper()
                nome = sol.get('solicitante', '')
                
                titulo_opcao = f"{status_icon} {header_prefix}{tipo} — {nome}"
                opcoes_radio.append(titulo_opcao)
                dict_sols[titulo_opcao] = sol
                
            selecionado = st.radio("Selecione um pedido:", opcoes_radio, label_visibility="collapsed")
        
    with col_details:
        with st.container(border=True):
            if selecionado:
                sol = dict_sols[selecionado]
                
                urgente = sol.get("urgencia", False)
                status = sol.get("status", "Pendente")
                
                # Parte Superior: Duas Colunas para dados rápidos
                st.subheader(selecionado.replace("⏳ ", "").replace("🚨 ", "").replace("✅ ", "").replace("❌ ", ""))
                
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write(f"**📍 Unidade / Órgão:** {sol.get('unidade')}")
                    st.write(f"**👤 Nome Solicitante:** {sol.get('solicitante')}")
                    if sol.get('postando_como'):
                        st.write(f"**🎭 Postando como:** {sol.get('postando_como')}")
                
                with col_info2:
                    st.write(f"**📅 Publicar em:** `{formatar_br(sol.get('data_publicacao'))}`")
                    st.write(f"**📢 Canais:** {sol.get('canais')}")
                    st.write(f"**🕒 Solicitado em:** {formatar_br(sol.get('data_solicitacao'))}")
                
                st.divider()
                
                # Parte Inferior: Uma Coluna para conteúdo denso
                with st.expander("📝 Descrição Detalhada"):
                    st.info(sol.get("descricao") or "Sem descrição fornecida.")
            
                # Exibição Inteligente em Grid de 4 Colunas
                anexos = sol.get("anexos", [])
                if anexos:
                    st.write("**📎 Materiais Anexados:**")
                    if isinstance(anexos, str): anexos = [anexos]
                
                    # Processamento em grupos de 4 para o grid
                    for i in range(0, len(anexos), 4):
                        cols = st.columns(4)
                        for j in range(4):
                            if i + j < len(anexos):
                                link = anexos[i + j]
                                l_lower = str(link).lower()
                                nome_arq = extrair_nome_arquivo(str(link))
                            
                                with cols[j]:
                                    # --- IMAGENS ---
                                    if any(ext in l_lower for ext in [".png", ".jpg", ".jpeg", ".webp"]) or ("alt=media" in l_lower and not any(a in l_lower for a in [".wav", ".mp3", ".pdf"])):
                                        st.image(link, use_container_width=True)
                                        st.markdown(f"🖼️ [**{nome_arq}**]({link})")
                                
                                    # --- ÁUDIOS ---
                                    elif any(ext in l_lower for ext in [".wav", ".mp3", ".ogg", "rec_"]):
                                        st.audio(link)
                                        st.markdown(f"🎵 [**{nome_arq}**]({link})")
                                    
                                    # --- PDFS ---
                                    elif ".pdf" in l_lower:
                                        st.markdown(f"📄 [**{nome_arq}**]({link})")
                                    
                                    # --- OUTROS ---
                                    else:
                                        st.markdown(f"🔗 [**{nome_arq}**]({link})")
            
                st.divider()
            
                # Ações de Gerenciamento
            
                # Botão para gerar a arte
                if st.button("Fazer Proposta de Conteúdo", key=f"ia_{sol['id']}", use_container_width=True, type="primary"):
                    if GEMINI_API_KEY_SECRET:
                        client = genai.Client(api_key=GEMINI_API_KEY_SECRET)
                        with st.status("⚙️ Estruturando Materiais da Solicitação...", expanded=True) as status_ia:
                            try:
                                tempo_inicio = time.time()
                                # 1. Preparar Conteúdo Multimodal
                                st.write("📥 Baixando e indexando anexos na base de dados...")
                                contents = []
                            
                                # Adiciona a descrição e metadados como texto
                                prompt_base = f"""
                                {INSTRUCAO_IDENTIDADE_TEXTO}
                                {INSTRUCAO_IDENTIDADE_VISUAL}
                            
                                DEMANDA DO USUÁRIO:
                                - TIPO: {sol.get('tipo')}
                                - SOLICITANTE/NOME: {sol.get('solicitante')}
                                - UNIDADE/ÓRGÃO: {sol.get('unidade')}
                                - POSTANDO COMO: {sol.get('postando_como', 'Não especificado')}
                                - DESCRIÇÃO: {sol.get('descricao')}
                            
                                INSTRUÇÃO FINAL: 
                                1. Gere uma LEGENDA completa e engajadora em Português.
                                2. Gere uma imagem para o post que siga a identidade visual correta.
                            
                                Retorne a legenda primeiro.
                                """
                                contents.append(prompt_base)
                                # Lista apenas com os anexos para reuso
                                anexos_parts = []
                                import tempfile
                                import os
                            
                                # Re-define anexos para garantir acesso dentro do botão
                                anexos_solicitacao = sol.get("anexos", [])
                                if isinstance(anexos_solicitacao, str): anexos_solicitacao = [anexos_solicitacao]

                                for link in anexos_solicitacao:
                                    l_low = str(link).lower()
                                    nome_arq = extrair_nome_arquivo(link)
                                    st.write(f"🔍 Preparando: **{nome_arq}**...")
                                
                                    # Determina MIME type oficial para upload via API Files
                                    m_type = None
                                    if ".pdf" in l_low: m_type = "application/pdf"
                                    elif ".png" in l_low: m_type = "image/png"
                                    elif any(x in l_low for x in [".jpg", ".jpeg"]): m_type = "image/jpeg"
                                    elif ".webp" in l_low: m_type = "image/webp"
                                    elif ".mp3" in l_low: m_type = "audio/mp3"
                                    elif ".wav" in l_low: m_type = "audio/wav"
                                    elif ".ogg" in l_low: m_type = "audio/ogg"
                                
                                    try:
                                        # Download e uso da API de Arquivos do Gemini (Protege contra limitação de Payload/Erro de Áudio)
                                        resp_file = requests.get(link)
                                        if resp_file.status_code == 200:
                                            ext = os.path.splitext(nome_arq)[1].lower()
                                            if not ext: ext = ".bin"
                                        
                                            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                                                tmp_file.write(resp_file.content)
                                                tmp_path = tmp_file.name
                                            
                                            st.write(f"☁️ Fazendo upload nativo (File API)...")
                                            gemini_file = client.files.upload(file=tmp_path)
                                            anexos_parts.append(gemini_file)
                                        
                                            # Cleanup do arquivo temporário
                                            try:
                                                os.remove(tmp_path)
                                            except:
                                                pass
                                            
                                            st.write(f"✅ Anexo processado e indexado com sucesso.")
                                        else:
                                            st.warning(f"⚠️ Não foi possível baixar '{nome_arq}' (Status {resp_file.status_code})")
                                    except Exception as e_dl:
                                        st.warning(f"⚠️ Erro ao tratar '{nome_arq}': {e_dl}")
                            
                                # 2. Gerar Texto Estruturado Multicanal
                                class TextosGerados(BaseModel):
                                    instagram: Optional[str] = Field(None, description="Texto formatado para Instagram com tom engajador (Máximo 3 emojis). Use parágrafos curtos separados por duas quebras de linha (\\n\\n). Inclua hashtags relacionadas na base.")
                                    whatsapp: Optional[str] = Field(None, description="Mensagem curta, direta e impactante para WhatsApp (Máximo 3 emojis). Pule linhas (\\n\\n). Use *negrito* nos destaques. OBRIGATÓRIO incluir ao final um Call-To-Action sugerindo: 'Acesse o site do Departamento para saber mais / ler a notícia completa'.")
                                    email: Optional[str] = Field(None, description="Disparo de e-mail institucional. ZERO EMOJIS. Saudação corporativa initial (ex 'Prezados,'), e encerramento com a Assinatura. O corpo deve ser descritivo com parágrafos BEM SEPARADOS por duas quebras de linha (\\n\\n).")
                                    linkedin: Optional[str] = Field(None, description="Publicação executiva/acadêmica. ZERO EMOJIS. Destaque marcos de sucesso usando marcadores (bullets). Use quebras de linha (\\n\\n) entre sessões com enfoque profissional, networking e inovação.")
                                    site: Optional[str] = Field(None, description="Matéria Jornalística COMPLETA para o portal web web. ZERO EMOJIS. O maior texto de todos gerados. Deve possuir Título forte na 1ª linha. Embaixo do título escreva o corpo da notícia com no mínimo 2 a 3 parágrafos bem recheados de contexto e divididos por duas quebras de linha (\\n\\n).")
                                
                                canais_solicitados = sol.get('canais', 'Não especificado')
                                
                                prompt_texto = f"""
                                {INSTRUCAO_IDENTIDADE_TEXTO}
                            
                                IMPORTANTE: O usuário quer publicar este conteúdo nos seguintes canais: {canais_solicitados}.
                                
                                REGRAS DE FORMATAÇÃO ESTRUTURAIS EXPLÍCITAS:
                                - **QUEBRAS DE LINHA**: É OBRIGATÓRIO o uso sequenciado de duas quebras de linha literais (\\n\\n) em todos os textos para gerar espaçamento/parágrafos de descanso visual, nada de textão sólido.
                                - **ESCALA DE TAMANHOS**: Garanta que o texto para SITE seja nitidamente o mais longo, rico e informativo, com cara de artigo, enquanto WAHTSAPP seja objetivo e sintético com foco em direcionamento para ler a notícia inteira no Site. O E-mail também deve ser médio-longo para comunicar formalmente.
                                - **USO RESTRITO DE EMOJIS**: Limite estritamente a NO MÁXIMO 3 emojis por texto (para canais como Instagram e WhatsApp). Canais formais como E-mail, Site e LinkedIn NÃO DEVEM possuir nenhum emoji!
                            
                                DEMANDA DO USUÁRIO:
                                - TIPO: {sol.get('tipo')}
                                - SOLICITANTE/NOME: {sol.get('solicitante')}
                                - UNIDADE/ÓRGÃO: {sol.get('unidade')}
                                - POSTANDO COMO: {sol.get('postando_como', 'Não especificado')}
                                - CANAIS ONDE SERÃO PUBLICADOS: {canais_solicitados}
                                - DESCRIÇÃO: {sol.get('descricao')}
                                """
                            
                                with st.spinner("✍️ Compilando e redigindo formato multicanal...", show_time=True):
                                    resp_text = client.models.generate_content(
                                        model="gemini-3.1-flash-lite-preview", 
                                        contents=anexos_parts + [prompt_texto],
                                        config=types.GenerateContentConfig(
                                            response_mime_type="application/json",
                                            response_schema=TextosGerados,
                                        ),
                                    )
                                    legenda_final = resp_text.text
                                    
                                    try:
                                        textos_parsed = json.loads(legenda_final)
                                    except:
                                        textos_parsed = {"instagram": legenda_final}
                                
                                st.write("✅ Textos redigidos com sucesso.")
                                
                                st.info("📋 **Copys Automáticos por Canal (Role para Visualizar)**")
                                if textos_parsed:
                                    mapping = [
                                        ("instagram", "📱 Instagram"),
                                        ("whatsapp", "💬 WhatsApp"),
                                        ("email", "✉️ E-mail"),
                                        ("linkedin", "💼 LinkedIn"),
                                        ("site", "🌐 Site")
                                    ]
                                    available_channels = [k for k, _ in mapping if textos_parsed.get(k)]
                                    labels = [l for k, l in mapping if textos_parsed.get(k)]
                                    
                                    if labels:
                                        tabs = st.tabs(labels)
                                        for idx, key in enumerate(available_channels):
                                            with tabs[idx]:
                                                st.write(textos_parsed[key])
                            
                                # Gerar Imagem
                                image_bytes = None
                                try:
                                    ambito_sol = sol.get('postando_como', 'Departamento')
                                    prefixo_template = "departamento"
                                    if "Colegiado" in ambito_sol: prefixo_template = "colegiado"
                                    elif "Pós" in ambito_sol: prefixo_template = "pos"
                                
                                    path_bg = os.path.join("assets", f"{prefixo_template}-background-template.png")
                                
                                    def up_img_safe(p):
                                        if os.path.exists(p): return client.files.upload(file=p)
                                        return None
                                
                                    file_bg = up_img_safe(path_bg)
                                
                                    anexos_imagem = list(anexos_parts)
                                    if file_bg: anexos_imagem.append(file_bg)
                                
                                    prompt_imagem = (
                                        f"Create an Instagram post image (portrait 4:5 aspect ratio).\n\n"
                                        f"INSTRUÇÕES DE DESIGN E LIBERDADE CRIATIVA:\n"
                                        f"1. VOCÊ TEM TOTAL LIBERDADE PARA CRIAR! O design deve ser moderno, chamativo, engajador e muito bonito visualmente.\n"
                                        f"2. Foi fornecido um 'background-template' apenas como base de cores e texturas. Use a essência desse fundo, mas sinta-se à vontade para inovar, compor elementos em 3D, adicionar grafismos e criar contrastes marcantes no post.\n"
                                        f"3. SE HOUVER FOTOS de pessoas/rostos nos arquivos fornecidos pelo usuário: O rosto deve permanecer INTACTO. Do NOT alter expressions, DO NOT add smiles or corrections. Copie as feições exatamente como estão na imagem original. Caso a foto seja muito ampla, faça um foco (recorte) no rosto da pessoa destacando-a no centro ou laterais do design.\n\n"
                                        f"DEMANDA DO USUÁRIO (O que exibir na arte):\n"
                                        f"TIPO: '{sol.get('tipo', '')}'\n"
                                        f"POSTANDO COMO: '{sol.get('postando_como', '')}'\n"
                                        f"DESCRIÇÃO E TEXTOS: '{sol.get('descricao', '')}'\n"
                                    )
                                
                                    with st.spinner("🎨 Renderizando arte visual (aspect ratio 4:5)...", show_time=True):
                                        resp_img = client.models.generate_content(
                                            model="gemini-3-pro-image-preview",
                                            contents=anexos_imagem + [prompt_imagem],
                                            config=types.GenerateContentConfig(
                                                response_modalities=['IMAGE'],
                                                image_config=types.ImageConfig(aspect_ratio="4:5", image_size="4K")
                                            )
                                        )
                                
                                    for part in resp_img.parts:
                                        if part.inline_data: image_bytes = part.inline_data.data; break
                                        elif hasattr(part, "as_image"):
                                            img_o = part.as_image()
                                            b_arr = io.BytesIO()
                                            img_o.save(b_arr, format='PNG')
                                            image_bytes = b_arr.getvalue()
                                            break
                                
                                    if image_bytes: 
                                        st.write("✅ Arte visual concluída.")
                                        st.image(image_bytes, caption="Prévia da Arte Gerada", width=300)
                                    else: 
                                        st.write("ℹ️ Apenas os textos da proposta puderam ser renderizados.")
                                except Exception as e_img:
                                    st.warning(f"Não foi possível gerar a arte visual: {e_img}")
                                    
                                # 3. Salvar resultados permanentemente no Banco de Dados
                                image_url = None
                                if image_bytes:
                                    st.write("☁️ Salvando arte no banco de dados...")
                                    nome_img = f"ia_gen_{sol['id']}_{int(time.time())}.png"
                                    image_url = upload_to_storage(image_bytes, nome_img, "image/png")
                            
                                tempo_total = round(time.time() - tempo_inicio, 1)
                            
                                # Preparar dicionário de dados da tentativa
                                nova_tent = {
                                    "legenda": legenda_final,
                                    "imagem_url": image_url,
                                    "prompt_texto": prompt_texto,
                                    "prompt_imagem": prompt_imagem,
                                    "tempo_segundos": tempo_total,
                                    "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                                }
                                
                                tentativas_atuais = sol.get("tentativas_ia", [])
                                lista_tents = []
                                for t in tentativas_atuais:
                                    if isinstance(t, dict):
                                        lista_tents.append(t)
                                    elif isinstance(t, str):
                                        try: lista_tents.append(json.loads(t))
                                        except: pass
                                
                                lista_tents.append(nova_tent)
                                
                                if atualizar_tentativas_ia(sol['id'], lista_tents):
                                    status_ia.update(label="✨ Rascunho finalizado e salvo no histórico! Atualizando...", state="complete")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    status_ia.update(label="⚠️ Rascunho gerado, mas erro ao salvar histórico.", state="error")
                                    
                            except Exception as e:
                                st.error(f"Erro inesperado no processamento de IA: {e}")
                                status_ia.update(label="❌ Erro no processamento", state="error")

            # Exibição do Histórico de Tentativas da IA
            tentativas_ia_banco = sol.get("tentativas_ia", [])
            if tentativas_ia_banco:
                st.markdown("---")
                st.markdown("### Propostas de Arte Geradas")
                
                lista_tents = []
                for t in tentativas_ia_banco:
                    if isinstance(t, dict):
                        lista_tents.append(t)
                    elif isinstance(t, str):
                        try: lista_tents.append(json.loads(t))
                        except: pass
                
                for idx, t in enumerate(reversed(lista_tents)):
                    num = len(lista_tents) - idx
                    # Expande apenas a tentativa mais recente (que agora é o índice 0)
                    with st.expander(f"Tentativa {num}", expanded=(idx == 0)):
                        c1, c2 = st.columns([1, 1.2])
                        with c1:
                            if t.get("imagem_url"):
                                st.image(t["imagem_url"], caption=f"Arte Gerada (Tentativa {num})", use_container_width=True)
                                st.markdown(f"📥 [Baixar Arte Original]({t['imagem_url']})")
                            else:
                                st.info("Arte visual não foi gerada ou salva.")
                        with c2:
                            st.markdown("**Textos Copys Gerados (Pronto para Uso):**")
                            # Renderiza textos estruturados multicanais ou legado plano
                            try:
                                textos_hist = json.loads(t.get("legenda", ""))
                                if isinstance(textos_hist, dict):
                                    mapping = [
                                        ("instagram", "📱 Instagram"),
                                        ("whatsapp", "💬 WhatsApp"),
                                        ("email", "✉️ E-mail"),
                                        ("linkedin", "� LinkedIn"),
                                        ("site", "🌐 Site")
                                    ]
                                    available_channels = [k for k, _ in mapping if textos_hist.get(k)]
                                    labels = [l for k, l in mapping if textos_hist.get(k)]
                                    
                                    if labels:
                                        tabs = st.tabs(labels)
                                        for idx, key in enumerate(available_channels):
                                            with tabs[idx]:
                                                st.text_area("Cópia", value=textos_hist[key], height=250, key=f"hs_{key}_{sol['id']}_{num}", label_visibility="collapsed")
                                                if key == "site":
                                                    st.markdown("---")
                                                    if st.button("🌐 Adicionar ao site", key=f"btn_add_site_{sol['id']}_{num}"):
                                                        linhas = textos_hist[key].strip().split('\n')
                                                        titulo = next((l for l in linhas if l.strip()), "Notícia do Departamento")
                                                        titulo = titulo.replace('*', '').replace('#', '').strip()
                                                        
                                                        doc_data = {
                                                            "titulo": titulo,
                                                            "conteudo": textos_hist[key],
                                                            "autor": "Departamento de Estatística - IME/UFBA",
                                                            "data": datetime.utcnow(),
                                                            "tipo": "noticia"
                                                        }
                                                        if t.get("imagem_url"):
                                                            doc_data["imagem_url"] = t["imagem_url"]
                                                            
                                                        sucesso, msg = adicionar_documento("conteudos", doc_data)
                                                        if sucesso:
                                                            st.success("✅ Notícia publicada no site com sucesso!")
                                                        else:
                                                            st.error(f"⚠️ Erro ao publicar: {msg}")
                                else:
                                    raise ValueError("Not a dict")
                            except:
                                # Caso antigo ou mal formatado
                                st.text_area(
                                    "Texto legado gerado:", 
                                    value=t.get("legenda", ""), 
                                    height=350, 
                                    key=f"hist_legenda_v1_{sol['id']}_{num}", 
                                    label_visibility="collapsed"
                                )
                            # Detalhes técnicos ocultos conforme nova UI

def page_adicionar_noticia():
    st.header("Publicar Nova Notícia")
    titulo = st.text_input("Título da Notícia")
    conteudo = st.text_area("Conteúdo da Notícia", height=200)
    autor = st.text_input("Autor", placeholder="Ex: Prof. Silva")
    capa = st.file_uploader("Capa da Notícia (Imagem Frontal)", type=["png", "jpg", "jpeg", "webp"])
    
    if st.button("Publicar Notícia"):
        if titulo and conteudo:
            data_atual = datetime.utcnow()
            doc_data = {
                "titulo": titulo,
                "conteudo": conteudo,
                "autor": autor,
                "data": data_atual,
                "tipo": "noticia"
            }
            
            # Se tiver imagem, sobe pro Firebase via File API/Storage
            if capa is not None:
                with st.spinner("☁️ Fazendo upload da Imagem de Capa..."):
                    img_bytes = capa.read()
                    import time
                    ext = capa.name.split('.')[-1]
                    nome_slug = titulo.lower().replace(' ', '_')[:20]
                    nome_arq = f"capa_{nome_slug}_{int(time.time())}.{ext}"
                    try:
                        url_capa = upload_to_storage(img_bytes, nome_arq, capa.type)
                        doc_data["imagem_url"] = url_capa
                    except Exception as e:
                        st.warning(f"Aviso: Erro inesperado ao hospedar imagem principal - {e}")
            
            adicionar_documento("conteudos", doc_data)
        else:
            st.warning("Preencha o título e o conteúdo!")

def page_gerenciar_instrucoes():
    st.header("Adicionar Instrução aos Docentes")
    instrucao_titulo = st.text_input("Assunto / Título")
    instrucao_detalhes = st.text_area("Detalhes da Instrução")
    prazo = st.date_input("Prazo de Execução (se houver)")
    
    if st.button("Enviar Instrução"):
        if instrucao_titulo and instrucao_detalhes:
            doc_data = {
                "titulo": instrucao_titulo,
                "detalhes": instrucao_detalhes,
                "prazo": str(prazo),
                "data_criacao": datetime.utcnow(),
                "tipo": "instrucao"
            }
            adicionar_documento("conteudos", doc_data)
        else:
            st.warning("Preencha título e detalhes!")


# ── Instruções de Identidade Visual (embarcadas no prompt) ──────────────────
# Todas as 3 identidades são passadas ao modelo para que ele mesmo classifique
# o tipo de postagem e aplique as cores/estilo corretos automaticamente.

INSTRUCAO_IDENTIDADE_VISUAL = """
You are designing an Instagram post for a university statistics department. There are THREE distinct visual identities. 
You MUST first analyze the post topic/content below and classify it into one of these categories, then apply the EXACT corresponding visual identity.

═══════════════════════════════════════════════════════════════
CLASSIFICATION RULES (read the user's demand and pick ONE):
═══════════════════════════════════════════════════════════════

CATEGORY A — "DEPARTAMENTO DE ESTATÍSTICA" (Blue/Gray identity)
  Use when: the post is about the department in general, faculty/professor matters, 
  departmental announcements, hiring, administrative topics, general events organized 
  by the department, seminars, divulgações gerais, monitorias, seleções de monitoria, 
  or anything that does NOT clearly belong to pós-graduação or the colegiado specifically.
  THIS IS THE DEFAULT — use it when unsure.

CATEGORY B — "COLEGIADO DE ESTATÍSTICA" (Purple identity)
  Use when: the post is specifically about the undergraduate program ("graduação"), 
  colegiado decisions, student council matters, undergraduate student events, 
  curriculum changes for the bachelor's program, or topics explicitly mentioning 
  "colegiado" or aimed at undergraduate students specifically.

CATEGORY C — "PÓS-GRADUAÇÃO EM ESTATÍSTICA" (Yellow/Gold identity)
  Use when: the post is about the graduate program ("pós-graduação", "mestrado", "doutorado"), 
  thesis defenses ("defesa de dissertação/tese"), research seminars for graduate students, 
  calls for graduate applications ("seleção de mestrado/doutorado"), or topics explicitly 
  mentioning "pós-graduação", "mestrado", or "doutorado".

═══════════════════════════════════════════════════════════════
═══════════════════════════════════════════════════════════════
DESIGN GUIDELINES (FLEXIBLE IDENTITY):
═══════════════════════════════════════════════════════════════

The goal is to follow a consistent "brand feel" without being a carbon copy. Use the attached templates as inspiration for the layout and style, but feel free to harmonize and vary the composition.

── GUIDELINE A: DEPARTAMENTO (Professional Blue/Steel) ──
• COLOR PALETTE: Dominated by blues (Navy, Royal, Steel) and metallic grays. Accents of white or very light ice-blue.
• VIBE: Institutional, clean, academic excellence.
• ELEMENTS: Use professional geometric shapes, subtle wireframe overlays, or modern data-visualization icons as background decorations.
• TYPOGRAPHY: Strong, clean sans-serif for titles. High contrast for readability.
• FOOTER: Must include "Departamento de Estatística — IME — UFBA".

── GUIDELINE B: COLEGIADO (Vibrant Purple/Gold) ──
• COLOR PALETTE: Deep purples, indigos, and lavenders paired with energetic golden-yellow accents.
• VIBE: Social, student-focused, modern, youthful.
• ELEMENTS: Dynamic arcs, dot-grids, or connected network patterns. The purple/gold contrast should be striking and engaging. 
• TYPOGRAPHY: Modern, bold, potentially using larger font sizes for impact.
• FOOTER: Must include "Colegiado de Estatística".

── GUIDELINE C: PÓS-GRADUAÇÃO (Prestigious Gold/Navy) ──
• COLOR PALETTE: Warm golds and amber yellows as the primary foundation, balanced with dark navy blue accents.
• VIBE: Prestigious, scholarly, elevated, inviting.
• ELEMENTS: Sophisticated geometric compositions. Think professional research posters but stylized for Instagram. Use circles and sharp lines to create depth.
• TYPOGRAPHY: Elegant but very bold sans-serif. Clear distinction between Title and Body.
• FOOTER: Must include "Pós-Graduação em Estatística — IME — UFBA".

GENERAL RULES FOR ALL:
1. Don't be afraid of gradients, shadows, and depth (2.5D style).
2. Ensure the text is always perfectly readable against the background.
3. Use modern, professional layouts (grid-based or asymmetrically balanced).
4. Artistic Freedom: If the user demand is a special event (like a party or a unique seminar), you can lean more into the theme while keeping the core category colors.
"""

INSTRUCAO_IDENTIDADE_TEXTO = """
Você é responsável pela comunicação do Departamento de Estatística do IME-UFBA no Instagram.
Existem 3 contextos possíveis. Analise a demanda do usuário e deduza qual é o contexto, depois adapte o tom:

- Se for sobre o DEPARTAMENTO em geral (eventos, avisos, divulgações, monitorias, seleções): 
  Use tom institucional e profissional. Assine como "Departamento de Estatística — IME/UFBA".

- Se for sobre o COLEGIADO (graduação, decisões do colegiado, alunos de graduação):
  Use tom mais jovem e engajador, voltado para graduandos. Assine como "Colegiado de Estatística".

- Se for sobre PÓS-GRADUAÇÃO (mestrado, doutorado, defesas, seminários de pesquisa):
  Use tom mais formal e acadêmico, voltado para pesquisadores. Assine como "Pós-Graduação em Estatística — IME/UFBA".
"""




def page_todas_solicitacoes():
    st.header("Solicitações Totais")
    todas_solicitacoes = listar_documentos("solicitacoes")
    
    if not todas_solicitacoes:
        st.info("Nenhuma solicitação encontrada no banco de dados.")
        return
        
    dados_formatados = []
    for sol in todas_solicitacoes:
        linha = sol.copy()
        
        # Remove as tentativas de IA do histórico 
        if "tentativas_ia" in linha:
            del linha["tentativas_ia"]
            
        # Puxa o URL do primeiro anexo para usar como Link clicável
        url_anexo = None
        if "anexos" in linha and isinstance(linha["anexos"], list) and len(linha["anexos"]) > 0:
            for a in linha["anexos"]:
                if isinstance(a, str) and a.startswith("http"):
                    url_anexo = a
                    break
        linha["anexos"] = url_anexo
             
        dados_formatados.append(linha)
    
    import pandas as pd
    df = pd.DataFrame(dados_formatados)
    
    # Converte strings ISO em objetos datetime nativos que o DatetimeColumn consegue re-formatar bonitinho 
    if "data_solicitacao" in df.columns:
        df["data_solicitacao"] = pd.to_datetime(df["data_solicitacao"], errors='coerce')
    if "data_publicacao" in df.columns:
        df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors='coerce')
    
    # Ordenação lógica das colunas para visualização mais fluida
    colunas_ordem = ["status", "data_solicitacao", "unidade", "postando_como", "solicitante", "email", "tipo", "data_publicacao", "descricao", "canais", "anexos"]
    cols_existentes = [c for c in colunas_ordem if c in df.columns]
    outras_cols = [c for c in df.columns if c not in colunas_ordem]
    df = df[cols_existentes + outras_cols]
    
    # Exibe a tabela interativa configurada utilizando st.column_config
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "id": None,          # Ocultar ID interno do firebase
            "urgencia": None,    # Ocultar (como pedido)
            "data_solicitacao": st.column_config.DatetimeColumn(
                "Solicitado Em", 
                format="DD/MM/YYYY - HH:mm",
                help="Data e hora exata da requisição",
                width="medium"
            ),
            "data_publicacao": st.column_config.DatetimeColumn(
                "Para Publicar Em", 
                format="DD/MM/YYYY - HH:mm",
                width="medium"
            ),
            "solicitante": st.column_config.TextColumn("Solicitante", width="medium"),
            "email": st.column_config.TextColumn("E-mail", width="large"),
            "unidade": st.column_config.TextColumn("Unidade", width="medium"),
            "tipo": st.column_config.TextColumn("Tipo", width="small"),
            "postando_como": st.column_config.TextColumn("Papel do Solicitante", width="medium"),
            "status": st.column_config.TextColumn("Status", width="small"),
            "descricao": st.column_config.TextColumn("Descrição da Demanda", width="large"),
            "canais": st.column_config.TextColumn("Canais", width="medium"),
            "anexos": st.column_config.LinkColumn(
                "🔗 Anexos (Base)",
                display_text="Abrir Arquivo 📥",
                help="Link para o arquivo original em nuvem",
                width="medium"
            )
        }
    )


# Montagem das Páginas e Menu Lateral
pg = st.navigation({
    "Central de Solicitações": [
        st.Page(page_solicitar_publicacao, title="Nova Solicitação de Divulgação", icon="📣", default=True),
        st.Page(page_todas_solicitacoes, title="Todas as Solicitações", icon="📋")
    ],
    "Em Construção": [
        st.Page(page_dashboard_solicitacoes, title="Gerador de Proposta de Conteúdo", icon="📊"),
        st.Page(page_adicionar_noticia, title="Publicar Notícia no site do DEST", icon="📰")
    ]
})

pg.run()

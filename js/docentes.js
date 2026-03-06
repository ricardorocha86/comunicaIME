/**
 * Docentes - Carrega dados do corpo docente a partir de planilha Google Sheets
 * A planilha deve estar publicada como CSV
 * 
 * NOTA: Quando executado localmente (file://), o navegador pode bloquear
 * requisições externas por CORS. Neste caso, usamos dados de fallback.
 * Em produção (servidor web), os dados são carregados dinamicamente.
 */

const DOCENTES_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQBZHD4_GQ9uJ-GMhnfuFvqE9zS6CTuS3TlA8pZ2qxJ3BYjg9AtYLYU1n8qelLnXcLJYqEHud2p038o/pub?gid=0&single=true&output=csv';

// Fallback data for local testing (when CORS blocks external requests)
const FALLBACK_DATA = [
    { 'Nome': 'Ricardo Rocha', 'E-mail': 'ricardo@ufba.br', 'Cargo': 'Professor' },
    { 'Nome': 'Denise Viola', 'E-mail': 'denise@ufba.br', 'Cargo': 'Professor' },
    { 'Nome': 'Raydonal Ospina', 'E-mail': 'raydonal@ufba.br', 'Cargo': 'Professor Titular' }
];

/**
 * Parse CSV string into array of objects
 */
function parseCSV(csvText) {
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) return [];

    // Get headers from first line
    const headers = lines[0].split(',').map(h => h.trim());

    // Parse data rows
    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim());
        if (values.length >= headers.length) {
            const row = {};
            headers.forEach((header, index) => {
                row[header] = values[index] || '';
            });
            data.push(row);
        }
    }

    return data;
}

/**
 * Create a docente card HTML
 */
function createDocenteCard(docente) {
    const nome = docente['Nome'] || 'Nome não informado';
    const email = docente['E-mail'] || '';
    const cargo = docente['Cargo'] || 'Professor';

    // Generate initials for avatar
    const initials = nome
        .split(' ')
        .filter(n => n.length > 0)
        .slice(0, 2)
        .map(n => n[0].toUpperCase())
        .join('');

    // Generate a consistent color based on name
    const colors = ['#1a5276', '#2980b9', '#16a085', '#27ae60', '#8e44ad', '#c0392b', '#d35400'];
    const colorIndex = nome.charCodeAt(0) % colors.length;
    const bgColor = colors[colorIndex];

    return `
        <div class="docente-card">
            <div class="docente-avatar" style="background-color: ${bgColor}">
                ${initials}
            </div>
            <div class="docente-info">
                <h3 class="docente-nome">${nome}</h3>
                <span class="docente-cargo">${cargo}</span>
                ${email ? `<a href="mailto:${email}" class="docente-email"><i class="fa-solid fa-envelope"></i> ${email}</a>` : ''}
            </div>
        </div>
    `;
}

/**
 * Render docentes to the grid
 */
function renderDocentes(docentes, gridEl) {
    if (docentes.length === 0) {
        return false;
    }

    // Sort by name
    docentes.sort((a, b) => (a['Nome'] || '').localeCompare(b['Nome'] || ''));

    // Render cards
    gridEl.innerHTML = docentes.map(createDocenteCard).join('');

    // Animate cards
    const cards = gridEl.querySelectorAll('.docente-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'all 0.4s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });

    return true;
}

/**
 * Load and display docentes
 */
async function loadDocentes() {
    const loadingEl = document.getElementById('docentes-loading');
    const errorEl = document.getElementById('docentes-error');
    const gridEl = document.getElementById('docentes-grid');

    if (!gridEl) return;

    let docentes = [];
    let usedFallback = false;

    try {
        // Try to fetch CSV data from Google Sheets
        const response = await fetch(DOCENTES_CSV_URL);

        if (!response.ok) {
            throw new Error('Falha ao carregar dados');
        }

        const csvText = await response.text();
        docentes = parseCSV(csvText);

    } catch (error) {
        console.warn('Não foi possível carregar dados externos, usando fallback:', error.message);
        // Use fallback data when CORS or network issues occur
        docentes = FALLBACK_DATA;
        usedFallback = true;
    }

    // Hide loading
    if (loadingEl) loadingEl.style.display = 'none';

    if (docentes.length === 0) {
        if (errorEl) {
            errorEl.innerHTML = '<i class="fa-solid fa-info-circle"></i> <span>Nenhum docente cadastrado.</span>';
            errorEl.style.display = 'flex';
        }
        return;
    }

    // Render docentes
    renderDocentes(docentes, gridEl);

    // Show notice if using fallback
    if (usedFallback) {
        console.info('Dados carregados do cache local. Para dados atualizados, hospede o site em um servidor web.');
    }
}

// Load docentes when DOM is ready
document.addEventListener('DOMContentLoaded', loadDocentes);

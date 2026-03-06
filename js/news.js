const FIRESTORE_PROJECT_ID = 'site-departamento';
const FIRESTORE_API_KEY = 'AIzaSyB8iObpp24XjY2o8KkdCyqAwXSix_en-1E';
const NEWS_ENDPOINT = `https://firestore.googleapis.com/v1/projects/${FIRESTORE_PROJECT_ID}/databases/(default)/documents/conteudos?key=${FIRESTORE_API_KEY}&pageSize=12`;

function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function getFieldValue(field) {
    if (!field || typeof field !== 'object') {
        return '';
    }

    if ('stringValue' in field) {
        return field.stringValue;
    }

    if ('timestampValue' in field) {
        return field.timestampValue;
    }

    return '';
}

function formatDate(value) {
    if (!value) {
        return '';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return '';
    }

    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
    }).format(date);
}

function summarizeText(value, maxLength = 170) {
    const normalized = String(value || '').replace(/\s+/g, ' ').trim();

    if (!normalized) {
        return 'Atualização institucional do Departamento de Estatística.';
    }

    if (normalized.length <= maxLength) {
        return normalized;
    }

    return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function createArticleHref(id) {
    return `pages/noticia.html?id=${encodeURIComponent(id)}`;
}

function normalizeFirestoreNews(document) {
    const fields = document?.fields || {};
    const type = getFieldValue(fields.tipo);
    const publishedAt = getFieldValue(fields.data_publicacao) || getFieldValue(fields.data);

    if (type && type !== 'noticia') {
        return null;
    }

    return {
        id: document?.name?.split('/').pop() || '',
        title: getFieldValue(fields.titulo) || 'Notícia do departamento',
        excerpt: summarizeText(getFieldValue(fields.conteudo)),
        content: getFieldValue(fields.conteudo),
        imageUrl: getFieldValue(fields.imagem_url),
        meta: getFieldValue(fields.autor) || 'Departamento de Estatística · IME / UFBA',
        publishedAt,
        articleHref: createArticleHref(document?.name?.split('/').pop() || ''),
    };
}

async function fetchNews() {
    const response = await fetch(NEWS_ENDPOINT, { cache: 'no-store' });

    if (!response.ok) {
        throw new Error(`Falha ao carregar notícias (${response.status})`);
    }

    const data = await response.json();
    const items = (data.documents || [])
        .map(normalizeFirestoreNews)
        .filter(Boolean)
        .sort((left, right) => new Date(right.publishedAt || 0) - new Date(left.publishedAt || 0));

    return items.slice(0, 5);
}

function renderNewsCard(item, variant) {
    const title = escapeHtml(item.title);
    const excerpt = escapeHtml(item.excerpt || '');
    const meta = escapeHtml(item.meta || 'Departamento de Estatística · IME / UFBA');
    const publishedAt = formatDate(item.publishedAt);
    const dateMarkup = publishedAt ? `<span>${escapeHtml(publishedAt)}</span>` : '';
    const tagName = item.articleHref ? 'a' : 'article';
    const cardAttributes = item.articleHref
        ? `class="news-card news-card-${variant}" href="${escapeHtml(item.articleHref)}"`
        : `class="news-card news-card-${variant}"`;
    const imageMarkup = item.imageUrl
        ? `<div class="news-card-media">
                <img src="${escapeHtml(item.imageUrl)}" alt="${title}" loading="lazy">
           </div>`
        : `<div class="news-card-media news-card-media-fallback" aria-hidden="true">
                <i class="fa-solid fa-chart-column"></i>
           </div>`;
    const titleMarkup = `<span class="news-card-title-link">${title}</span>`;
    const ctaMarkup = item.articleHref
        ? `<span class="news-card-cta">Ler notícia</span>`
        : '';

    return `
        <${tagName} ${cardAttributes}>
            ${imageMarkup}
            <div class="news-card-content">
                <div class="news-card-meta">
                    <span>${meta}</span>
                    ${dateMarkup}
                </div>
                <h3 class="news-card-title">${titleMarkup}</h3>
                <p class="news-card-excerpt">${excerpt}</p>
                ${ctaMarkup}
            </div>
        </${tagName}>
    `;
}

function renderNews(container, items) {
    if (!items.length) {
        container.innerHTML = `
            <div class="news-empty">
                <i class="fa-regular fa-newspaper" aria-hidden="true"></i>
                <p>Sem notícias disponíveis no momento.</p>
            </div>
        `;
        return;
    }

    const [featured, ...secondary] = items;

    container.innerHTML = `
        <div class="news-stack">
            ${renderNewsCard(featured, 'featured')}
            <div class="news-grid">
                ${secondary.map((item) => renderNewsCard(item, 'compact')).join('')}
            </div>
        </div>
    `;
}

document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('news-container');
    if (!container) {
        return;
    }

    try {
        const items = await fetchNews();
        renderNews(container, items);
    } catch (error) {
        container.innerHTML = `
            <div class="news-empty">
                <i class="fa-regular fa-newspaper" aria-hidden="true"></i>
                <p>Não foi possível carregar as notícias no momento.</p>
            </div>
        `;
    }
});

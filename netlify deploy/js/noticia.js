const NEWS_PROJECT_ID = 'site-departamento';
const NEWS_API_KEY = 'AIzaSyB8iObpp24XjY2o8KkdCyqAwXSix_en-1E';

function getDocumentFieldValue(field) {
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

function escapeArticleHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatInlineText(value) {
    const escaped = escapeArticleHtml(value);
    return escaped.replace(/(https?:\/\/[^\s<]+)/g, (url) => {
        return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
    });
}

function formatArticleDate(value) {
    if (!value) {
        return 'Data não informada';
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return 'Data não informada';
    }

    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date);
}

function normalizeText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function renderArticleBody(value, title = '') {
    const blocks = String(value || '')
        .split(/\n\s*\n/)
        .map((block) => block.trim())
        .filter(Boolean);

    if (!blocks.length) {
        return '<p>Conteúdo da notícia indisponível.</p>';
    }

    const normalizedTitle = normalizeText(title);
    let leadRendered = false;

    return blocks
        .filter((block, index) => !(index === 0 && normalizeText(block) === normalizedTitle))
        .map((block) => {
            const lines = block
                .split('\n')
                .map((line) => line.trim())
                .filter(Boolean);

            if (!lines.length) {
                return '';
            }

            if (lines.every((line) => /^[-•]\s+/.test(line))) {
                return `
                    <ul class="article-list">
                        ${lines.map((line) => `<li>${formatInlineText(line.replace(/^[-•]\s+/, ''))}</li>`).join('')}
                    </ul>
                `;
            }

            if (lines.every((line) => /^\d+[.)]\s+/.test(line))) {
                return `
                    <ol class="article-list article-list-numbered">
                        ${lines.map((line) => `<li>${formatInlineText(line.replace(/^\d+[.)]\s+/, ''))}</li>`).join('')}
                    </ol>
                `;
            }

            if (lines.length === 1 && lines[0].length <= 72 && !/[.!?]$/.test(lines[0])) {
                return `<h2 class="article-subtitle">${formatInlineText(lines[0])}</h2>`;
            }

            if (lines.length === 1 && lines[0].length <= 160 && /^[“"'].*[”"']$/.test(lines[0])) {
                return `<blockquote class="article-quote">${formatInlineText(lines[0])}</blockquote>`;
            }

            const paragraphClass = leadRendered ? '' : ' class="article-lead"';
            leadRendered = true;
            return `<p${paragraphClass}>${formatInlineText(lines.join('<br>'))}</p>`;
        })
        .join('');
}

async function fetchArticleById(id) {
    const endpoint = `https://firestore.googleapis.com/v1/projects/${NEWS_PROJECT_ID}/databases/(default)/documents/conteudos/${encodeURIComponent(id)}?key=${NEWS_API_KEY}`;
    const response = await fetch(endpoint, { cache: 'no-store' });

    if (!response.ok) {
        throw new Error(`Falha ao carregar notícia (${response.status})`);
    }

    const document = await response.json();
    const fields = document?.fields || {};
    const type = getDocumentFieldValue(fields.tipo);

    if (type && type !== 'noticia') {
        throw new Error('Documento não é uma notícia');
    }

    return {
        title: getDocumentFieldValue(fields.titulo) || 'Notícia do departamento',
        content: getDocumentFieldValue(fields.conteudo),
        imageUrl: getDocumentFieldValue(fields.imagem_url),
        author: getDocumentFieldValue(fields.autor) || 'Departamento de Estatística - IME/UFBA',
        publishedAt: getDocumentFieldValue(fields.data_publicacao) || getDocumentFieldValue(fields.data),
    };
}

function showErrorState() {
    const loading = document.getElementById('news-article-loading');
    const article = document.getElementById('news-article');
    const error = document.getElementById('news-article-error');

    if (loading) {
        loading.hidden = true;
    }

    if (article) {
        article.hidden = true;
    }

    if (error) {
        error.hidden = false;
    }
}

function renderArticle(article) {
    const loading = document.getElementById('news-article-loading');
    const articleNode = document.getElementById('news-article');
    const error = document.getElementById('news-article-error');
    const hero = document.querySelector('.article-hero');
    const cover = document.getElementById('news-cover');
    const coverImage = document.getElementById('news-cover-image');
    const breadcrumbTitle = document.getElementById('news-breadcrumb-title');
    const title = document.getElementById('news-title');
    const date = document.getElementById('news-date');
    const author = document.getElementById('news-author');
    const dateAside = document.getElementById('news-date-aside');
    const authorAside = document.getElementById('news-author-aside');
    const body = document.getElementById('news-body');
    const formattedDate = formatArticleDate(article.publishedAt);

    document.title = `${article.title} - DEst | IME/UFBA`;

    if (title) {
        title.textContent = article.title;
    }

    if (breadcrumbTitle) {
        breadcrumbTitle.textContent = article.title;
    }

    if (date) {
        date.textContent = formattedDate;
    }

    if (author) {
        author.textContent = article.author;
    }

    if (dateAside) {
        dateAside.textContent = formattedDate;
    }

    if (authorAside) {
        authorAside.textContent = article.author;
    }

    if (body) {
        body.innerHTML = renderArticleBody(article.content, article.title);
    }

    if (cover && coverImage && article.imageUrl) {
        cover.hidden = false;
        coverImage.src = article.imageUrl;
        coverImage.alt = article.title;
        if (hero) {
            hero.classList.remove('article-hero-no-cover');
        }
    } else if (hero) {
        hero.classList.add('article-hero-no-cover');
    }

    if (loading) {
        loading.hidden = true;
    }

    if (error) {
        error.hidden = true;
    }

    if (articleNode) {
        articleNode.hidden = false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');

    if (!id) {
        showErrorState();
        return;
    }

    try {
        const article = await fetchArticleById(id);
        renderArticle(article);
    } catch (error) {
        showErrorState();
    }
});

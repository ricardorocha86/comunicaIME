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

function summarizeArticle(value, maxLength = 280) {
    const normalized = String(value || '').replace(/\s+/g, ' ').trim();

    if (!normalized) {
        return 'Publicação institucional do Departamento de Estatística.';
    }

    if (normalized.length <= maxLength) {
        return normalized;
    }

    return `${normalized.slice(0, maxLength).trimEnd()}...`;
}

function renderArticleBody(value) {
    const blocks = String(value || '')
        .split(/\n\s*\n/)
        .map((block) => block.trim())
        .filter(Boolean);

    if (!blocks.length) {
        return '<p>Conteúdo da notícia indisponível.</p>';
    }

    return blocks
        .map((block) => `<p>${escapeArticleHtml(block).replace(/\n/g, '<br>')}</p>`)
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
    const summary = document.getElementById('news-summary');
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

    if (summary) {
        summary.textContent = summarizeArticle(article.content);
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
        body.innerHTML = renderArticleBody(article.content);
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

function getCurrentPage() {
    return window.location.pathname.split('/').pop() || '';
}

function getSidebarMarkup() {
    return `
        <section class="panel nav-panel">
            <div class="panel-heading">
                <h2>Menu principal</h2>
                <button class="sidebar-close" id="mobile-menu-close" type="button" aria-label="Fechar menu principal">
                    <i class="fa-solid fa-xmark" aria-hidden="true"></i>
                </button>
            </div>

            <nav class="sidebar-menu">
                <a class="menu-home" href="../index.html">Home</a>

                <div class="menu-group">
                    <h3>Departamento</h3>
                    <a href="institucional.html">Institucional</a>
                    <a href="historico.html">Histórico</a>
                    <a href="pessoas.html#corpo-docente">Corpo docente</a>
                </div>

                <div class="menu-group">
                    <h3>Ensino</h3>
                    <a href="graduacao.html">Graduação</a>
                    <a href="pos-graduacao.html">Pós-graduação</a>
                </div>

                <div class="menu-group">
                    <h3>Pesquisa</h3>
                    <a href="pesquisa.html">Linhas de pesquisa</a>
                    <a href="producao-academica.html">Produção acadêmica</a>
                </div>

                <div class="menu-group">
                    <h3>Extensão</h3>
                    <a href="consultoria.html">Consultoria</a>
                    <a href="extensao.html#cursos">Cursos</a>
                </div>

                <div class="menu-group">
                    <h3>Laboratórios</h3>
                    <a href="laboratorios.html#lema">LEMA</a>
                    <a href="laboratorios.html#cer">CER</a>
                    <a href="laboratorios.html#sally">Sally</a>
                    <a href="laboratorios.html#linca">LinCa</a>
                </div>

                <div class="menu-group menu-group-social">
                    <h3>Redes sociais</h3>
                    <div class="social-links">
                        <a href="https://www.facebook.com/departamentoestatistica/" target="_blank" rel="noopener noreferrer" aria-label="Facebook">
                            <i class="fa-brands fa-facebook-f" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.instagram.com/dest_ufba/" target="_blank" rel="noopener noreferrer" aria-label="Instagram">
                            <i class="fa-brands fa-instagram" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.youtube.com/@destufba" target="_blank" rel="noopener noreferrer" aria-label="YouTube">
                            <i class="fa-brands fa-youtube" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.linkedin.com/company/dest-ufba" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn">
                            <i class="fa-brands fa-linkedin-in" aria-hidden="true"></i>
                        </a>
                    </div>
                </div>
            </nav>
        </section>
    `;
}

function getHeaderMarkup() {
    return `
        <div class="header-container">
            <div class="brand-logo-wrap">
                <a class="brand-logo" href="../index.html" aria-label="Página inicial do Departamento de Estatística">
                    <img src="../assets/logoest.png" alt="Logo do Departamento de Estatística do IME UFBA">
                </a>
            </div>

            <div class="brand-copy-wrap">
                <a class="brand-copy" href="../index.html">
                    <strong>Departamento de Estatística</strong>
                    <small>Instituto de Matemática e Estatística · UFBA</small>
                </a>

                <button class="mobile-menu-toggle" id="mobile-menu-toggle" type="button" aria-controls="primary-sidebar" aria-expanded="false">
                    <i class="fa-solid fa-bars" aria-hidden="true"></i>
                    <span>Menu</span>
                </button>

                <div class="header-social-cta" aria-label="Acesso rápido às redes sociais">
                    <div class="header-social-copy">
                        <span>Acompanhe o DEst</span>
                        <small>Editais, notícias e agenda nas nossas redes</small>
                    </div>

                    <div class="header-social-links">
                        <a href="https://www.instagram.com/dest_ufba/" target="_blank" rel="noopener noreferrer" aria-label="Instagram do Departamento de Estatística">
                            <i class="fa-brands fa-instagram" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.facebook.com/departamentoestatistica/" target="_blank" rel="noopener noreferrer" aria-label="Facebook do Departamento de Estatística">
                            <i class="fa-brands fa-facebook-f" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.youtube.com/@destufba" target="_blank" rel="noopener noreferrer" aria-label="YouTube do Departamento de Estatística">
                            <i class="fa-brands fa-youtube" aria-hidden="true"></i>
                        </a>
                        <a href="https://www.linkedin.com/company/dest-ufba" target="_blank" rel="noopener noreferrer" aria-label="LinkedIn do Departamento de Estatística">
                            <i class="fa-brands fa-linkedin-in" aria-hidden="true"></i>
                        </a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function getFooterMarkup() {
    return `
        <div class="shell footer-shell">
            <div class="footer-contact">
                <strong>Departamento de Estatística · IME / UFBA</strong>
                <p>Avenida Milton Santos, s/n, Ondina, Salvador - BA</p>
                <p>Tel: (71) 3283-6262 / 3283-6341 · <a href="mailto:dest@ufba.br">dest@ufba.br</a></p>
            </div>

            <img src="../assets/barra_de_logos.png" alt="Logos do NEX IME, Departamento de Estatística, Instituto de Matemática e Estatística e UFBA">
        </div>
    `;
}

function renderUnifiedLayout() {
    const header = document.querySelector('.top-header');
    const sidebar = document.querySelector('.modern-sidebar');
    const footer = document.querySelector('.main-footer');

    if (!header || !sidebar || !footer) {
        return;
    }

    header.className = 'legacy-header top-header';
    header.innerHTML = getHeaderMarkup();

    sidebar.className = 'sidebar sidebar-left modern-sidebar';
    sidebar.id = 'primary-sidebar';
    sidebar.setAttribute('aria-label', 'Navegação principal');
    sidebar.innerHTML = getSidebarMarkup();

    let overlay = document.getElementById('sidebar-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay internal-sidebar-overlay';
        overlay.id = 'sidebar-overlay';
        overlay.hidden = true;
        header.insertAdjacentElement('afterend', overlay);
    }

    footer.className = 'legacy-footer main-footer';
    footer.innerHTML = getFooterMarkup();
}

function setupInternalMobileNavigation() {
    const sidebar = document.getElementById('primary-sidebar');
    const headerContainer = document.querySelector('.header-container');
    const openButton = document.getElementById('mobile-menu-toggle');
    const closeButton = document.getElementById('mobile-menu-close');
    const overlay = document.getElementById('sidebar-overlay');
    const mobileMediaQuery = window.matchMedia('(max-width: 1060px)');

    if (!sidebar || !headerContainer || !openButton || !closeButton || !overlay) {
        return;
    }

    let lastFocusedElement = null;
    const isOpen = () => document.body.classList.contains('internal-menu-open');

    const closeMenu = () => {
        if (!isOpen()) {
            return;
        }

        document.body.classList.remove('internal-menu-open');
        overlay.hidden = true;

        if (lastFocusedElement instanceof HTMLElement) {
            lastFocusedElement.focus();
        }
    };

    const openMenu = () => {
        if (!mobileMediaQuery.matches) {
            return;
        }

        lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        overlay.hidden = false;
        document.body.classList.add('internal-menu-open');
        closeButton.focus();
    };

    openButton.addEventListener('click', () => {
        if (isOpen()) {
            closeMenu();
            return;
        }

        openMenu();
    });

    closeButton.addEventListener('click', closeMenu);
    overlay.addEventListener('click', closeMenu);

    sidebar.addEventListener('click', (event) => {
        if (!mobileMediaQuery.matches) {
            return;
        }

        const target = event.target instanceof Element ? event.target.closest('a') : null;
        if (target) {
            closeMenu();
        }
    });

    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    const handleViewportChange = () => {
        if (!mobileMediaQuery.matches) {
            document.body.classList.remove('internal-menu-open');
            overlay.hidden = true;
        }
    };

    if (typeof mobileMediaQuery.addEventListener === 'function') {
        mobileMediaQuery.addEventListener('change', handleViewportChange);
    } else {
        mobileMediaQuery.addListener(handleViewportChange);
    }

    handleViewportChange();
}

document.addEventListener('DOMContentLoaded', () => {
    renderUnifiedLayout();
    setupInternalMobileNavigation();
});

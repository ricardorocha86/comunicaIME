function setupSlideshow() {
    const slides = Array.from(document.querySelectorAll('.slide'));
    const tabs = Array.from(document.querySelectorAll('.slide-tab'));
    const prevButton = document.getElementById('slide-prev');
    const nextButton = document.getElementById('slide-next');

    if (!slides.length || !tabs.length) {
        return;
    }

    let currentIndex = 0;
    let timerId = null;

    const showSlide = (index) => {
        currentIndex = (index + slides.length) % slides.length;

        slides.forEach((slide, slideIndex) => {
            slide.classList.toggle('is-active', slideIndex === currentIndex);
        });

        tabs.forEach((tab, tabIndex) => {
            tab.classList.toggle('is-active', tabIndex === currentIndex);
        });
    };

    const restartTimer = () => {
        if (timerId) {
            window.clearInterval(timerId);
        }

        timerId = window.setInterval(() => {
            showSlide(currentIndex + 1);
        }, 5000);
    };

    tabs.forEach((tab) => {
        tab.addEventListener('click', () => {
            const nextIndex = Number(tab.dataset.slide || 0);
            showSlide(nextIndex);
            restartTimer();
        });
    });

    if (prevButton) {
        prevButton.addEventListener('click', () => {
            showSlide(currentIndex - 1);
            restartTimer();
        });
    }

    if (nextButton) {
        nextButton.addEventListener('click', () => {
            showSlide(currentIndex + 1);
            restartTimer();
        });
    }

    showSlide(0);
    restartTimer();
}

function setupMobileNavigation() {
    const sidebar = document.getElementById('primary-sidebar');
    const openButton = document.getElementById('mobile-menu-toggle');
    const closeButton = document.getElementById('mobile-menu-close');
    const overlay = document.getElementById('sidebar-overlay');
    const mobileMediaQuery = window.matchMedia('(max-width: 1060px)');

    if (!sidebar || !openButton || !closeButton || !overlay) {
        return;
    }

    let lastFocusedElement = null;

    const isMenuOpen = () => document.body.classList.contains('menu-open');

    const syncMenuState = (open) => {
        document.body.classList.toggle('menu-open', open);
        openButton.setAttribute('aria-expanded', String(open));
        sidebar.setAttribute('aria-hidden', String(!open && mobileMediaQuery.matches));
        overlay.hidden = !open;

        if (open) {
            lastFocusedElement = document.activeElement instanceof HTMLElement ? document.activeElement : null;
            closeButton.focus();
            return;
        }

        if (lastFocusedElement instanceof HTMLElement) {
            lastFocusedElement.focus();
        }
    };

    const closeMenu = () => {
        if (!isMenuOpen()) {
            return;
        }

        syncMenuState(false);
    };

    const openMenu = () => {
        if (!mobileMediaQuery.matches) {
            return;
        }

        syncMenuState(true);
    };

    openButton.addEventListener('click', () => {
        if (isMenuOpen()) {
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
        if (mobileMediaQuery.matches) {
            sidebar.setAttribute('aria-hidden', String(!isMenuOpen()));
            overlay.hidden = !isMenuOpen();
            return;
        }

        syncMenuState(false);
        sidebar.setAttribute('aria-hidden', 'false');
    };

    if (typeof mobileMediaQuery.addEventListener === 'function') {
        mobileMediaQuery.addEventListener('change', handleViewportChange);
    } else {
        mobileMediaQuery.addListener(handleViewportChange);
    }

    handleViewportChange();
}

document.addEventListener('DOMContentLoaded', () => {
    setupSlideshow();
    setupMobileNavigation();
});

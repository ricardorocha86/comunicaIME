document.addEventListener('DOMContentLoaded', () => {
    // Toggle submenus within the modern sidebar
    const navGroups = document.querySelectorAll('.nav-group');

    navGroups.forEach(group => {
        const toggleBtn = group.querySelector('.nav-item.has-dropdown');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                // Close other open menus (accordion behavior)
                navGroups.forEach(otherGroup => {
                    if (otherGroup !== group) {
                        otherGroup.classList.remove('open');
                    }
                });
                
                // Toggle current group
                group.classList.toggle('open');
            });
        }
    });

    // Search box placeholder animation
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
        const placeholders = ['Buscar projetos...', 'Pesquisar notícias...', 'Encontrar servidores...'];
        let index = 0;

        setInterval(() => {
            index = (index + 1) % placeholders.length;
            searchInput.placeholder = placeholders[index];
        }, 3500);
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;

            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

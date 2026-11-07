// Menu de configurações da conta (<details>): fecha ao clicar fora dele ou ao apertar Esc. Abrir e fechar pelo
// próprio botão já é nativo do <details>; aqui só se acrescenta o fechamento "por fora", sem tocar em estilos.
const menu = document.querySelector('.account-menu');

if (menu) {
    document.addEventListener('click', (event) => {
        if (menu.open && !menu.contains(event.target)) {
            menu.open = false;
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && menu.open) {
            menu.open = false;
            menu.querySelector('summary').focus();
        }
    });
}

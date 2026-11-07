// Antes de salvar um usuário novo, uma janela pede para conferir o e-mail informado (é para ele que o convite
// será enviado). O servidor valida tudo de novo: se o navegador não suportar <dialog>, o formulário segue direto.
const form = document.querySelector('[data-email-confirm-form]');
const dialog = document.getElementById('email-confirm-dialog');

if (form && dialog && typeof dialog.showModal === 'function') {
    const address = document.getElementById('email-confirm-address');
    let confirmed = false;

    form.addEventListener('submit', (event) => {
        if (confirmed) {
            return;
        }
        const email = form.elements['email'].value.trim();
        const confirmation = form.elements['email_confirmation'].value.trim();
        // Se os dois e-mails não conferem, deixa o servidor mostrar o erro, sem abrir a janela.
        if (email.toLowerCase() !== confirmation.toLowerCase()) {
            return;
        }
        event.preventDefault();
        address.textContent = email;
        dialog.showModal();
    });

    dialog.querySelector('[data-confirm]').addEventListener('click', () => {
        confirmed = true;
        dialog.close();
        form.requestSubmit();
    });
    dialog.querySelector('[data-cancel]').addEventListener('click', () => dialog.close());
}

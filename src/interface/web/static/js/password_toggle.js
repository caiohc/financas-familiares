// Mostrar/ocultar a senha digitada. Cada botão [data-password-toggle] aponta (pelo id) para o
// campo que controla. Só troca o tipo do campo e os atributos de acessibilidade; a aparência do
// ícone (olho aberto ou riscado) vem do CSS, a partir de aria-pressed.
document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const input = document.getElementById(button.dataset.passwordToggle);
    if (!input) {
        return;
    }
    button.addEventListener('click', () => {
        const reveal = input.type === 'password';
        input.type = reveal ? 'text' : 'password';
        button.setAttribute('aria-pressed', String(reveal));
        button.setAttribute('aria-label', reveal ? 'Ocultar senha' : 'Mostrar senha');
    });
});

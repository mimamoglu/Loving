// Auto-dismiss flash messages after 4 seconds
document.querySelectorAll('.flash-msg').forEach(msg => {
    setTimeout(() => {
        msg.style.opacity = '0';
        msg.style.transform = 'translateX(100%)';
        setTimeout(() => msg.remove(), 300);
    }, 4000);
});

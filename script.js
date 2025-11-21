// Элементы DOM
const loadingScreen = document.getElementById('loadingScreen');
const mainScreen = document.getElementById('mainScreen');
const userAvatar = document.getElementById('userAvatar');
const userName = document.getElementById('userName');
const wildBalance = document.getElementById('wildBalance');
const notificationsBtn = document.querySelector('.notifications-btn');
const notificationsDropdown = document.querySelector('.notifications-dropdown');
const closeDropdown = document.querySelector('.close-dropdown');
const promoClose = document.querySelector('.promo-close');
const openAccountBtn = document.getElementById('openAccount');
const qrBtn = document.getElementById('showQR');
const makeTransferBtn = document.getElementById('makeTransfer');
const openDepositBtn = document.getElementById('openDeposit');
const devModal = document.getElementById('devModal');
const closeModal = document.querySelector('.close-modal');
const transferAnimation = document.getElementById('transferAnimation');
const transferSound = document.getElementById('transferSound');

// Данные пользователя
let userData = {
    firstName: 'Пользователь',
    lastName: '',
    photo: '',
    balance: 2500
};

// Инициализация приложения
async function initApp() {
    try {
        // Инициализируем VK Bridge
        await vkBridge.send('VKWebAppInit');
        
        // Получаем данные пользователя
        const user = await vkBridge.send('VKWebAppGetUserInfo');
        
        // Сохраняем данные
        userData = {
            firstName: user.first_name,
            lastName: user.last_name,
            photo: user.photo_200 || user.photo_100,
            balance: generateRandomBalance()
        };

        // Обновляем интерфейс
        updateUserInterface();
        
        // Показываем основной экран с задержкой для анимации
        setTimeout(showMainScreen, 2000);
        
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        // Fallback данные
        userData.photo = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2RjMjYyNiIvPjx0ZXh0IHg9IjEwMCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+VXNlcjwvdGV4dD48L3N2Zz4=';
        updateUserInterface();
        setTimeout(showMainScreen, 2000);
    }
}

// Обновление интерфейса
function updateUserInterface() {
    // Аватар и имя
    userAvatar.src = userData.photo;
    userAvatar.alt = `${userData.firstName} ${userData.lastName}`;
    userName.textContent = userData.firstName;
    
    // Баланс с анимацией
    animateBalance(wildBalance, userData.balance);
}

// Анимация баланса
function animateBalance(element, targetBalance) {
    let currentBalance = 0;
    const duration = 2000;
    const stepTime = 20;
    const steps = duration / stepTime;
    const increment = targetBalance / steps;
    
    const timer = setInterval(() => {
        currentBalance += increment;
        if (currentBalance >= targetBalance) {
            currentBalance = targetBalance;
            clearInterval(timer);
        }
        element.textContent = Math.floor(currentBalance).toLocaleString('ru-RU');
    }, stepTime);
}

// Показать основной экран
function showMainScreen() {
    loadingScreen.classList.add('hidden');
    mainScreen.classList.remove('hidden');
    
    // Добавляем анимации для карточек
    animateCards();
}

// Анимация появления карточек
function animateCards() {
    const cards = document.querySelectorAll('.promo-section, .balance-section, .transfer-section, .deposit-section');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.2}s`;
    });
}

// Генерация случайного баланса
function generateRandomBalance() {
    return Math.floor(Math.random() * 15000) + 5000;
}

// Анимация перевода
function showTransferAnimation() {
    // Показываем анимацию
    transferAnimation.classList.remove('hidden');
    
    // Проигрываем звук
    try {
        transferSound.currentTime = 0;
        transferSound.play().catch(e => console.log('Audio play failed:', e));
    } catch (error) {
        console.log('Sound error:', error);
    }
    
    // Создаем эффект частиц
    createParticles();
    
    // Автоматически скрываем через 3 секунды
    setTimeout(() => {
        transferAnimation.classList.add('hidden');
        
        // Обновляем баланс после перевода
        const newBalance = userData.balance + 1500;
        userData.balance = newBalance;
        wildBalance.textContent = newBalance.toLocaleString('ru-RU');
        
    }, 3000);
}

// Создание частиц для анимации
function createParticles() {
    const animationContent = document.querySelector('.animation-content');
    
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.innerHTML = '💰';
        particle.style.position = 'absolute';
        particle.style.fontSize = '20px';
        particle.style.left = '50%';
        particle.style.top = '50%';
        particle.style.opacity = '1';
        particle.style.transform = 'translate(-50%, -50%)';
        particle.style.animation = `particleFloat ${Math.random() * 2 + 1}s ease-out forwards`;
        
        animationContent.appendChild(particle);
        
        // Удаляем частицу после анимации
        setTimeout(() => {
            particle.remove();
        }, 3000);
    }
}

// Добавляем CSS для частиц
const particleStyle = document.createElement('style');
particleStyle.textContent = `
    @keyframes particleFloat {
        0% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 1;
        }
        100% {
            transform: translate(
                ${Math.random() * 200 - 100}px, 
                ${Math.random() * 200 - 100}px
            ) scale(0);
            opacity: 0;
        }
    }
`;
document.head.appendChild(particleStyle);

// Обработчики событий
function setupEventListeners() {
    // Уведомления
    notificationsBtn.addEventListener('click', toggleNotifications);
    closeDropdown.addEventListener('click', closeNotifications);
    
    // Закрытие промо-блока
    promoClose.addEventListener('click', closePromo);
    
    // Кнопки "В разработке"
    openAccountBtn.addEventListener('click', showDevModal);
    qrBtn.addEventListener('click', showDevModal);
    openDepositBtn.addEventListener('click', showDevModal);
    
    // Анимация перевода
    makeTransferBtn.addEventListener('click', showTransferAnimation);
    
    // Модальное окно
    closeModal.addEventListener('click', hideDevModal);
    devModal.addEventListener('click', (e) => {
        if (e.target === devModal) hideDevModal();
    });
    
    // Закрытие уведомлений по клику вне области
    document.addEventListener('click', (e) => {
        if (!notificationsBtn.contains(e.target) && !notificationsDropdown.contains(e.target)) {
            closeNotifications();
        }
    });
    
    // Навигация
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            showDevModal();
        });
    });
    
    // Закрытие анимации перевода по клику
    transferAnimation.addEventListener('click', () => {
        transferAnimation.classList.add('hidden');
    });
}

// Управление уведомлениями
function toggleNotifications(e) {
    e.stopPropagation();
    const isHidden = notificationsDropdown.classList.contains('hidden');
    
    if (isHidden) {
        notificationsDropdown.classList.remove('hidden');
        notificationsBtn.style.background = 'var(--dark-red)';
    } else {
        closeNotifications();
    }
}

function closeNotifications() {
    notificationsDropdown.classList.add('hidden');
    notificationsBtn.style.background = 'var(--primary-red)';
}

// Закрытие промо-блока
function closePromo() {
    const promoSection = document.querySelector('.promo-section');
    promoSection.style.animation = 'fadeOut 0.5s ease-out forwards';
    setTimeout(() => {
        promoSection.remove();
    }, 500);
}

// Модальное окно "В разработке"
function showDevModal() {
    devModal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function hideDevModal() {
    devModal.classList.add('hidden');
    document.body.style.overflow = 'auto';
}

// Добавляем CSS анимацию для fadeOut
const fadeOutStyle = document.createElement('style');
fadeOutStyle.textContent = `
    @keyframes fadeOut {
        from { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
        }
        to { 
            opacity: 0; 
            transform: translateY(-20px) scale(0.9); 
        }
    }
`;
document.head.appendChild(fadeOutStyle);

// VK Bridge события
vkBridge.subscribe((e) => {
    if (e.detail.type === 'VKWebAppUpdateConfig') {
        const scheme = e.detail.data.scheme;
        document.body.setAttribute('scheme', scheme);
    }
});

// Запуск приложения
document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupEventListeners();
});

// Обработка ошибок VK Bridge
vkBridge.send('VKWebAppInit').catch((error) => {
    console.log('VKWebAppInit failed, running in standalone mode:', error);
    // Запускаем с тестовыми данными
    userData.photo = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2RjMjYyNiIvPjx0ZXh0IHg9IjEwMCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjAiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+VXNlcjwvdGV4dD48L3N2Zz4=';
    userData.firstName = 'Демо';
    userData.balance = 12450;
    updateUserInterface();
    setTimeout(showMainScreen, 2000);
    setupEventListeners();
});

// Service Worker для оффлайн работы (опционально)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(console.error);
}

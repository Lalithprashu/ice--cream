// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Navbar color change on scroll
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.background = 'rgba(255, 107, 107, 0.95)';
    } else {
        navbar.style.background = 'linear-gradient(135deg, var(--primary-color), var(--secondary-color))';
    }
});

// Animate elements on scroll
const animateOnScroll = () => {
    const elements = document.querySelectorAll('.menu-card, .about-section h2, .about-section p, .contact-form');
    
    elements.forEach(element => {
        const elementTop = element.getBoundingClientRect().top;
        const elementBottom = element.getBoundingClientRect().bottom;
        
        if (elementTop < window.innerHeight && elementBottom > 0) {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }
    });
};

// Initialize animation styles
document.addEventListener('DOMContentLoaded', () => {
    const elements = document.querySelectorAll('.menu-card, .about-section h2, .about-section p, .contact-form');
    elements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'all 0.6s ease-out';
    });
});

// Add scroll event listener
window.addEventListener('scroll', animateOnScroll);

// Form submission handling
const contactForm = document.querySelector('.contact-form');
if (contactForm) {
    contactForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);
        
        try {
            const response = await fetch('/api/contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            // Show success message
            const successMessage = document.createElement('div');
            successMessage.className = 'alert alert-success mt-3';
            successMessage.textContent = result.message;
            
            this.appendChild(successMessage);
            this.reset();
            
            // Remove success message after 5 seconds
            setTimeout(() => {
                successMessage.remove();
            }, 5000);
        } catch (error) {
            console.error('Error:', error);
            alert('There was an error sending your message. Please try again.');
        }
    });
}

// Add to cart animation
function addToCart(iceCreamId) {
    const button = event.target;
    
    // Create a small ice cream icon
    const icon = document.createElement('i');
    icon.className = 'fas fa-ice-cream';
    icon.style.position = 'fixed';
    icon.style.left = button.getBoundingClientRect().left + 'px';
    icon.style.top = button.getBoundingClientRect().top + 'px';
    icon.style.color = '#FF6B6B';
    icon.style.fontSize = '20px';
    icon.style.zIndex = '1000';
    document.body.appendChild(icon);
    
    // Animate the icon to the cart
    const cartPosition = { x: window.innerWidth - 50, y: 20 };
    icon.style.transition = 'all 0.5s ease-in-out';
    
    setTimeout(() => {
        icon.style.left = cartPosition.x + 'px';
        icon.style.top = cartPosition.y + 'px';
        icon.style.transform = 'scale(1.5)';
        
        // Remove the icon after animation
        setTimeout(() => {
            icon.remove();
        }, 500);
    }, 100);
}

// Parallax effect for hero section
window.addEventListener('scroll', () => {
    const hero = document.querySelector('.hero-section');
    const scrolled = window.pageYOffset;
    hero.style.backgroundPositionY = scrolled * 0.5 + 'px';
});

// Cart functionality
document.addEventListener('DOMContentLoaded', function() {
    // Category filtering
    const categoryLinks = document.querySelectorAll('.list-group-item');
    const productCards = document.querySelectorAll('.product-card');

    categoryLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const category = this.dataset.category;
            
            categoryLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');

            productCards.forEach(card => {
                if (category === 'all' || card.dataset.category === category) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });

    // Shopping cart functionality
    const cartModal = new bootstrap.Modal(document.getElementById('cartModal'));
    const cartItems = document.getElementById('cart-items');
    const cartTotal = document.getElementById('cart-total');
    const checkoutBtn = document.getElementById('checkout-btn');

    // Update cart display
    function updateCartDisplay() {
        fetch('/api/cart/items')
            .then(response => {
                if (!response.ok) {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                cartItems.innerHTML = '';
                let total = 0;

                data.items.forEach(item => {
                    total += item.total;
                    cartItems.innerHTML += `
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div>
                                <h6 class="mb-0">${item.name}</h6>
                                <small class="text-muted">₹${item.price.toFixed(2)} x ${item.quantity}</small>
                            </div>
                            <div>
                                <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart(${item.id})">Remove</button>
                            </div>
                        </div>
                    `;
                });

                cartTotal.textContent = total.toFixed(2);
                checkoutBtn.style.display = data.items.length > 0 ? 'inline-block' : 'none';
            })
            .catch(error => {
                console.error('Error:', error);
                cartItems.innerHTML = '<div class="alert alert-danger">Error loading cart items. Please try again.</div>';
            });
    }

    // Add to cart
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    addToCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: 1
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateCartDisplay();
                    cartModal.show();
                } else {
                    alert('Error adding item to cart: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error adding item to cart');
            });
        });
    });

    // Remove from cart
    const removeFromCartButtons = document.querySelectorAll('.remove-from-cart');
    removeFromCartButtons.forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.dataset.productId;
            fetch('/api/cart/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({
                    product_id: productId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateCartDisplay();
                } else {
                    alert('Error removing item from cart: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error removing item from cart');
            });
        });
    });

    // Initial cart display
    updateCartDisplay();
}); 
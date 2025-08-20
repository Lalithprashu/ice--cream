# Sweet Scoops Ice Cream Delight Website

A modern, responsive, and dynamic ice cream delight website built with Flask and Bootstrap 5, featuring colorful designs and interactive elements.

## Features

- 🎨 Modern and colorful design with gradient backgrounds
- 📱 Fully responsive layout for all devices
- ✨ Smooth animations and transitions
- 🛒 Interactive "Add to Cart" animations
- 📝 Contact form with validation
- 🌟 Parallax scrolling effects
- 🎯 Smooth scroll navigation
- 🎭 Dynamic navbar that changes on scroll
- 🔄 Real-time form submission handling
- 📊 API endpoints for data management

## Technologies Used

- Python 3.x
- Flask
- HTML5
- CSS3 (with CSS Variables and Flexbox)
- JavaScript (ES6+)
- Bootstrap 5
- Font Awesome Icons

## Project Structure

```
ice-cream-delight/
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── static/            # Static files
│   ├── styles.css     # Custom CSS styles
│   └── script.js      # JavaScript functionality
└── templates/         # Flask templates
    └── index.html     # Main HTML template
```

## Getting Started

1. Clone this repository or download the files
2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Flask application:
   ```bash
   python app.py
   ```
5. Open your web browser and navigate to `http://localhost:5000`

## API Endpoints

- `GET /`: Home page
- `GET /api/ice-creams`: Get all ice cream flavors
- `POST /api/contact`: Submit contact form

## Customization

### Colors
You can customize the website's color scheme by modifying the CSS variables in `static/styles.css`:

```css
:root {
    --primary-color: #FF6B6B;
    --secondary-color: #4ECDC4;
    --accent-color: #FFE66D;
    --dark-color: #2C3E50;
}
```

### Ice Cream Flavors
Edit the `ice_creams` list in `app.py` to modify the available flavors:

```python
ice_creams = [
    {
        'id': 1,
        'name': 'Vanilla Dream',
        'description': 'Classic vanilla with Madagascar vanilla beans',
        'image': 'image_url',
        'price': 5.99
    },
    # Add more flavors here
]
```

### Images
Replace the placeholder images in the `ice_creams` data with your own image URLs.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Opera (latest)

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details.
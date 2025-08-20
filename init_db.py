from app import app, db, Product

def init_db():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if we already have products
        if Product.query.first() is None:
            # Add sample products
            products = [
                Product(
                    name='Vanilla Delight',
                    description='Classic vanilla ice cream',
                    price=99.99,
                    image_url='https://example.com/vanilla.jpg'
                ),
                Product(
                    name='Chocolate Dream',
                    description='Rich chocolate ice cream',
                    price=129.99,
                    image_url='https://example.com/chocolate.jpg'
                ),
                Product(
                    name='Strawberry Sorbet',
                    description='Refreshing strawberry sorbet',
                    price=119.99,
                    image_url='https://example.com/strawberry.jpg'
                )
            ]
            
            for product in products:
                db.session.add(product)
            
            db.session.commit()
            print("Sample products added successfully!")
        else:
            print("Products already exist in the database.")

if __name__ == '__main__':
    init_db() 
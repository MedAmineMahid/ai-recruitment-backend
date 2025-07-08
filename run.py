import logging
from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
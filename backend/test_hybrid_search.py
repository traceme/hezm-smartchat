"""
Test script for hybrid search functionality.

This script tests:
1. BM25 keyword search
2. Hybrid search with different fusion methods
3. Query analysis and optimization
4. Search comparison functionality
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from services.hybrid_search import hybrid_search_engine, KeywordSearchEngine
from services.text_splitter import semantic_splitter
from services.embedding_service import embedding_service
from database import SessionLocal
from models.document import Document, DocumentChunk
import tempfile
import json

# Sample document content for testing
SAMPLE_DOCUMENTS = {
    "ml_guide": """
# Machine Learning Complete Guide

## What is Machine Learning?
Machine learning is a subset of artificial intelligence (AI) that focuses on algorithms and statistical models that enable computer systems to improve their performance on a specific task through experience, without being explicitly programmed.

### Core Concepts
- **Training Data**: Historical data used to train the model
- **Features**: Input variables used to make predictions
- **Labels**: Known output values for supervised learning
- **Algorithms**: Mathematical procedures that find patterns

## Types of Machine Learning

### Supervised Learning
In supervised learning, algorithms learn from labeled training data to make predictions or classifications on new, unseen data.

**Classification Examples:**
- Email spam detection
- Medical diagnosis
- Image recognition
- Sentiment analysis

**Regression Examples:**
- House price prediction
- Stock market forecasting
- Temperature prediction
- Sales revenue estimation

### Unsupervised Learning
Unsupervised learning finds hidden patterns in data without labeled examples.

**Key Techniques:**
1. **Clustering**: Grouping similar data points (K-means, hierarchical clustering)
2. **Dimensionality Reduction**: Reducing data complexity (PCA, t-SNE)
3. **Association Rules**: Finding relationships between variables
4. **Anomaly Detection**: Identifying outliers and unusual patterns

### Reinforcement Learning
Reinforcement learning involves an agent learning to make decisions by receiving rewards or penalties for actions taken in an environment.

**Applications:**
- Game playing (Chess, Go, video games)
- Robotics and autonomous systems
- Trading algorithms
- Recommendation systems optimization

## Popular Algorithms

### Linear Models
```python
from sklearn.linear_model import LinearRegression, LogisticRegression

# Linear Regression for continuous values
linear_model = LinearRegression()
linear_model.fit(X_train, y_train)

# Logistic Regression for classification
logistic_model = LogisticRegression()
logistic_model.fit(X_train, y_train)
```

### Tree-Based Methods
```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

# Decision Tree
tree_model = DecisionTreeClassifier()
tree_model.fit(X_train, y_train)

# Random Forest
forest_model = RandomForestClassifier(n_estimators=100)
forest_model.fit(X_train, y_train)
```

### Neural Networks
```python
from sklearn.neural_network import MLPClassifier
import tensorflow as tf

# Simple neural network
nn_model = MLPClassifier(hidden_layer_sizes=(100, 50))
nn_model.fit(X_train, y_train)

# Deep learning with TensorFlow
model = tf.keras.Sequential([
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10, activation='softmax')
])
```

## Evaluation Metrics

### Classification Metrics
- **Accuracy**: Percentage of correct predictions
- **Precision**: True positives / (True positives + False positives)
- **Recall**: True positives / (True positives + False negatives)
- **F1-Score**: Harmonic mean of precision and recall

### Regression Metrics
- **Mean Squared Error (MSE)**: Average of squared differences
- **Mean Absolute Error (MAE)**: Average of absolute differences
- **R-squared**: Coefficient of determination

## Best Practices

### Data Preparation
1. **Data Cleaning**: Handle missing values, outliers, and inconsistencies
2. **Feature Engineering**: Create meaningful features from raw data
3. **Data Splitting**: Separate training, validation, and test sets
4. **Scaling**: Normalize features for better algorithm performance

### Model Selection
1. **Cross-Validation**: Use k-fold CV for reliable performance estimates
2. **Hyperparameter Tuning**: Optimize model parameters
3. **Ensemble Methods**: Combine multiple models for better performance
4. **Regularization**: Prevent overfitting with L1/L2 regularization

### Deployment Considerations
- **Model Monitoring**: Track performance in production
- **A/B Testing**: Compare model versions
- **Data Drift**: Monitor for changes in input data distribution
- **Scalability**: Ensure models can handle production load

## Industry Applications

### Healthcare
- **Medical Imaging**: X-ray and MRI analysis for disease detection
- **Drug Discovery**: Accelerating pharmaceutical research
- **Personalized Medicine**: Tailoring treatments to individual patients
- **Epidemic Prediction**: Modeling disease spread patterns

### Finance
- **Fraud Detection**: Identifying suspicious transactions
- **Algorithmic Trading**: Automated investment strategies
- **Credit Scoring**: Assessing loan default risk
- **Risk Management**: Portfolio optimization and risk assessment

### Technology
- **Search Engines**: Ranking and relevance algorithms
- **Recommendation Systems**: Netflix, Amazon, Spotify suggestions
- **Natural Language Processing**: Chatbots and language translation
- **Computer Vision**: Autonomous vehicles and facial recognition

### Retail and E-commerce
- **Demand Forecasting**: Inventory management and planning
- **Price Optimization**: Dynamic pricing strategies
- **Customer Segmentation**: Targeted marketing campaigns
- **Supply Chain**: Logistics and distribution optimization

## Future Trends

### Emerging Technologies
- **Explainable AI**: Making model decisions interpretable
- **Federated Learning**: Training on distributed data
- **AutoML**: Automated machine learning pipeline creation
- **Edge Computing**: Running models on mobile and IoT devices

### Ethical Considerations
- **Bias and Fairness**: Ensuring models don't discriminate
- **Privacy**: Protecting sensitive user data
- **Transparency**: Making AI decisions understandable
- **Accountability**: Establishing responsibility for AI decisions

## Getting Started

### Learning Path
1. **Mathematics Foundation**: Statistics, linear algebra, calculus
2. **Programming Skills**: Python, R, SQL
3. **Core Concepts**: Study fundamental algorithms
4. **Hands-on Practice**: Work on real projects and datasets
5. **Specialization**: Choose focus areas (NLP, computer vision, etc.)

### Recommended Tools
- **Python Libraries**: scikit-learn, pandas, numpy, matplotlib
- **Deep Learning**: TensorFlow, PyTorch, Keras
- **Data Visualization**: seaborn, plotly, bokeh
- **Development**: Jupyter notebooks, Git, Docker

Machine learning continues to evolve rapidly, offering powerful tools for solving complex problems across industries. Success requires combining theoretical understanding with practical experience and staying current with emerging trends and best practices.
""",
    
    "python_tutorial": """
# Python Programming Tutorial

## Introduction to Python

Python is a high-level, interpreted programming language known for its simplicity and readability. Created by Guido van Rossum in 1991, Python has become one of the most popular programming languages for web development, data science, artificial intelligence, and automation.

### Why Choose Python?
- **Easy to Learn**: Simple, readable syntax
- **Versatile**: Suitable for many applications
- **Large Community**: Extensive libraries and support
- **Cross-platform**: Runs on Windows, macOS, Linux
- **Open Source**: Free to use and modify

## Basic Syntax and Data Types

### Variables and Assignment
```python
# Variable assignment
name = "Alice"
age = 30
height = 5.6
is_student = True

# Multiple assignment
x, y, z = 1, 2, 3
```

### Data Types
```python
# Numbers
integer_num = 42
float_num = 3.14
complex_num = 2 + 3j

# Strings
single_quotes = 'Hello'
double_quotes = "World"
multiline = '''This is a
multiline string'''

# Boolean
is_true = True
is_false = False
```

### Lists and Collections
```python
# Lists (mutable, ordered)
fruits = ['apple', 'banana', 'orange']
numbers = [1, 2, 3, 4, 5]
mixed = ['hello', 42, True, 3.14]

# Tuples (immutable, ordered)
coordinates = (10, 20)
rgb_color = (255, 128, 0)

# Dictionaries (key-value pairs)
person = {
    'name': 'John',
    'age': 25,
    'city': 'New York'
}

# Sets (unique elements)
unique_numbers = {1, 2, 3, 4, 5}
```

## Control Flow

### Conditional Statements
```python
# If-elif-else
temperature = 25

if temperature > 30:
    print("It's hot!")
elif temperature > 20:
    print("It's warm")
else:
    print("It's cool")

# Ternary operator
status = "hot" if temperature > 30 else "not hot"
```

### Loops
```python
# For loops
for i in range(5):
    print(i)

for fruit in fruits:
    print(fruit)

# While loops
count = 0
while count < 5:
    print(count)
    count += 1

# List comprehensions
squares = [x**2 for x in range(10)]
even_squares = [x**2 for x in range(10) if x % 2 == 0]
```

## Functions

### Basic Functions
```python
def greet(name):
    return f"Hello, {name}!"

def add_numbers(a, b=0):
    return a + b

# Function with variable arguments
def sum_all(*args):
    return sum(args)

# Function with keyword arguments
def create_profile(**kwargs):
    return kwargs

# Lambda functions
square = lambda x: x**2
```

### Advanced Function Features
```python
# Decorators
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Function took {end - start:.2f} seconds")
        return result
    return wrapper

@timer
def slow_function():
    import time
    time.sleep(1)
    return "Done"
```

## Object-Oriented Programming

### Classes and Objects
```python
class Car:
    def __init__(self, make, model, year):
        self.make = make
        self.model = model
        self.year = year
        self.odometer_reading = 0
    
    def get_descriptive_name(self):
        return f"{self.year} {self.make} {self.model}"
    
    def read_odometer(self):
        print(f"This car has {self.odometer_reading} miles on it.")
    
    def update_odometer(self, mileage):
        if mileage >= self.odometer_reading:
            self.odometer_reading = mileage
        else:
            print("You can't roll back an odometer!")

# Creating and using objects
my_car = Car('audi', 'a4', 2019)
print(my_car.get_descriptive_name())
my_car.update_odometer(23500)
my_car.read_odometer()
```

### Inheritance
```python
class ElectricCar(Car):
    def __init__(self, make, model, year):
        super().__init__(make, model, year)
        self.battery_size = 75
    
    def describe_battery(self):
        print(f"This car has a {self.battery_size}-kWh battery.")
    
    def fill_gas_tank(self):
        print("This car doesn't need a gas tank!")

# Using inheritance
my_tesla = ElectricCar('tesla', 'model s', 2019)
my_tesla.describe_battery()
```

## File Handling and Error Management

### File Operations
```python
# Reading files
with open('example.txt', 'r') as file:
    content = file.read()
    print(content)

# Writing files
data = ['line 1', 'line 2', 'line 3']
with open('output.txt', 'w') as file:
    for line in data:
        file.write(line + '\\n')

# JSON handling
import json

data = {'name': 'John', 'age': 30}
with open('data.json', 'w') as file:
    json.dump(data, file)

with open('data.json', 'r') as file:
    loaded_data = json.load(file)
```

### Exception Handling
```python
try:
    result = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
except Exception as e:
    print(f"An error occurred: {e}")
else:
    print("No errors occurred")
finally:
    print("This always executes")

# Custom exceptions
class CustomError(Exception):
    pass

def validate_age(age):
    if age < 0:
        raise CustomError("Age cannot be negative")
    return age
```

## Popular Libraries

### Data Science Libraries
```python
# NumPy for numerical computing
import numpy as np
array = np.array([1, 2, 3, 4, 5])
matrix = np.array([[1, 2], [3, 4]])

# Pandas for data manipulation
import pandas as pd
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['NY', 'LA', 'Chicago']
})

# Matplotlib for plotting
import matplotlib.pyplot as plt
plt.plot([1, 2, 3, 4], [1, 4, 9, 16])
plt.show()
```

### Web Development
```python
# Flask for web applications
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return '<h1>Hello, World!</h1>'

@app.route('/user/<name>')
def user(name):
    return f'<h1>Hello, {name}!</h1>'

if __name__ == '__main__':
    app.run(debug=True)
```

### API and Requests
```python
# Making HTTP requests
import requests

response = requests.get('https://api.github.com/users/octocat')
if response.status_code == 200:
    data = response.json()
    print(data['name'])

# POST request
payload = {'key1': 'value1', 'key2': 'value2'}
response = requests.post('https://httpbin.org/post', data=payload)
```

## Best Practices

### Code Style (PEP 8)
```python
# Good naming conventions
def calculate_total_price(item_price, tax_rate):
    return item_price * (1 + tax_rate)

# Use descriptive variable names
user_count = 100
is_valid_email = True

# Proper spacing and indentation
if user_count > 50:
    print("Many users")
    
# List comprehensions for simple operations
even_numbers = [x for x in range(20) if x % 2 == 0]
```

### Documentation and Testing
```python
def fibonacci(n):
    """
    Generate the nth Fibonacci number.
    
    Args:
        n (int): Position in Fibonacci sequence
        
    Returns:
        int: The nth Fibonacci number
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Unit testing
import unittest

class TestFibonacci(unittest.TestCase):
    def test_base_cases(self):
        self.assertEqual(fibonacci(0), 0)
        self.assertEqual(fibonacci(1), 1)
    
    def test_sequence(self):
        self.assertEqual(fibonacci(5), 5)
        self.assertEqual(fibonacci(10), 55)

if __name__ == '__main__':
    unittest.main()
```

## Advanced Topics

### Generators and Iterators
```python
# Generator function
def countdown(n):
    while n > 0:
        yield n
        n -= 1

# Generator expression
squares = (x**2 for x in range(10))

# Custom iterator
class Counter:
    def __init__(self, limit):
        self.limit = limit
        self.current = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current < self.limit:
            self.current += 1
            return self.current
        raise StopIteration
```

### Context Managers
```python
# Custom context manager
class FileManager:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
    
    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

# Using the context manager
with FileManager('test.txt', 'w') as f:
    f.write('Hello, World!')
```

Python's versatility and extensive ecosystem make it an excellent choice for beginners and experienced developers alike. Whether you're building web applications, analyzing data, or developing machine learning models, Python provides the tools and libraries to accomplish your goals efficiently.
"""
}

async def test_keyword_search():
    """Test BM25 keyword search functionality."""
    print("🔍 Testing BM25 Keyword Search...")
    
    # Prepare test chunks
    chunks = []
    for doc_id, (title, content) in enumerate(SAMPLE_DOCUMENTS.items(), 1):
        text_chunks = semantic_splitter.split_text(content, document_id=doc_id)
        for chunk in text_chunks:
            chunks.append({
                "document_id": doc_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type,
                "section_header": chunk.section_header,
                "token_count": chunk.token_count,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset
            })
    
    print(f"✅ Prepared {len(chunks)} chunks for keyword search")
    
    # Test queries
    test_queries = [
        "machine learning algorithms",
        "Python programming syntax",
        "supervised learning classification",
        "neural networks TensorFlow",
        "file handling exceptions"
    ]
    
    keyword_engine = KeywordSearchEngine()
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        
        results = keyword_engine.search(query, chunks, limit=5)
        
        print(f"   Found {len(results)} results:")
        for i, (chunk_id, score, chunk_data) in enumerate(results):
            print(f"   {i+1}. Score: {score:.3f} | Type: {chunk_data['chunk_type']}")
            print(f"      Preview: {chunk_data['content'][:100]}...")
    
    return chunks

async def test_hybrid_search_methods():
    """Test different hybrid search fusion methods."""
    print("\n🔀 Testing Hybrid Search Fusion Methods...")
    
    # Store sample documents in vector database
    doc_id = 999
    chunks = semantic_splitter.split_text(SAMPLE_DOCUMENTS["ml_guide"], document_id=doc_id)
    
    # Store chunks with embeddings
    result = await embedding_service.store_document_chunks(
        chunks=chunks, 
        document_id=doc_id, 
        user_id=1
    )
    print(f"✅ Stored {result['chunks_stored']} chunks in vector database")
    
    # Test query
    query = "What are the different types of machine learning algorithms?"
    
    # Test different fusion methods
    fusion_methods = ["weighted", "rrf", "max"]
    
    for method in fusion_methods:
        print(f"\n🧪 Testing {method.upper()} fusion:")
        
        results = await hybrid_search_engine.hybrid_search(
            query=query,
            user_id=1,
            document_id=doc_id,
            limit=5,
            vector_weight=0.7,
            keyword_weight=0.3,
            fusion_method=method,
            db_session=None  # Skip database metadata for this test
        )
        
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"   {i+1}. Hybrid: {result.hybrid_score:.3f} | Vector: {result.vector_score:.3f} | Keyword: {result.keyword_score:.3f}")
            print(f"      Type: {result.chunk_type} | Preview: {result.content[:80]}...")
    
    return doc_id

async def test_query_analysis():
    """Test query analysis and optimization."""
    print("\n🧠 Testing Query Analysis...")
    
    test_queries = [
        "What is machine learning?",  # Question, semantic heavy
        "Python syntax variables",   # Keyword heavy
        "neural networks TensorFlow", # Technical terms
        '"supervised learning"',      # Quoted phrase
        "explain deep learning concepts",  # Semantic heavy
        "find clustering algorithms"  # Keyword heavy
    ]
    
    for query in test_queries:
        analysis = hybrid_search_engine._analyze_query(query)
        
        print(f"\nQuery: '{query}'")
        print(f"  - Is question: {analysis['is_question']}")
        print(f"  - Semantic heavy: {analysis['is_semantic_heavy']}")
        print(f"  - Keyword heavy: {analysis['is_keyword_heavy']}")
        print(f"  - Has quotes: {analysis['has_quotes']}")
        print(f"  - Technical terms: {analysis['has_technical_terms']}")
        print(f"  - Word count: {analysis['word_count']}")

async def test_search_comparison():
    """Test search method comparison."""
    print("\n📊 Testing Search Method Comparison...")
    
    doc_id = 999  # Using the same document from previous test
    query = "How do neural networks work in deep learning?"
    
    # Vector search only
    print("\n1. Vector Search Only:")
    vector_results = await embedding_service.search_similar_chunks(
        query_text=query,
        user_id=1,
        document_id=doc_id,
        limit=3,
        score_threshold=0.1
    )
    for i, result in enumerate(vector_results):
        print(f"   {i+1}. Score: {result['score']:.3f} | {result['content'][:100]}...")
    
    # Keyword search only
    print("\n2. Keyword Search Only:")
    chunks_data = []
    chunks_info = await embedding_service.get_document_chunks_info(doc_id)
    if "error" not in chunks_info:
        for chunk in chunks_info['chunks']:
            chunks_data.append({
                "document_id": doc_id,
                "chunk_index": chunk['chunk_index'],
                "content": chunk['content'],
                "chunk_type": chunk['chunk_type'],
                "section_header": chunk.get('section_header'),
                "token_count": chunk['token_count'],
                "start_offset": 0,
                "end_offset": len(chunk['content'])
            })
        
        keyword_results = hybrid_search_engine._keyword_search(query, chunks_data, 3)
        for i, result in enumerate(keyword_results):
            print(f"   {i+1}. Score: {result['keyword_score']:.3f} | {result['content'][:100]}...")
    
    # Hybrid search
    print("\n3. Hybrid Search (Weighted):")
    hybrid_results = await hybrid_search_engine.hybrid_search(
        query=query,
        user_id=1,
        document_id=doc_id,
        limit=3,
        vector_weight=0.7,
        keyword_weight=0.3,
        fusion_method="weighted",
        db_session=None
    )
    for i, result in enumerate(hybrid_results):
        print(f"   {i+1}. Hybrid: {result.hybrid_score:.3f} (V:{result.vector_score:.3f}, K:{result.keyword_score:.3f})")
        print(f"      {result.content[:100]}...")

async def test_weight_optimization():
    """Test different weight combinations."""
    print("\n⚖️ Testing Weight Optimization...")
    
    doc_id = 999
    query = "machine learning classification algorithms"
    
    weight_combinations = [
        (1.0, 0.0),  # Vector only
        (0.8, 0.2),  # Vector heavy
        (0.6, 0.4),  # Balanced towards vector
        (0.5, 0.5),  # Balanced
        (0.4, 0.6),  # Balanced towards keyword
        (0.2, 0.8),  # Keyword heavy
        (0.0, 1.0),  # Keyword only
    ]
    
    for vector_weight, keyword_weight in weight_combinations:
        if vector_weight == 0.0 and keyword_weight == 1.0:
            # Skip pure keyword for this test as it requires different handling
            continue
            
        results = await hybrid_search_engine.hybrid_search(
            query=query,
            user_id=1,
            document_id=doc_id,
            limit=3,
            vector_weight=vector_weight,
            keyword_weight=keyword_weight,
            fusion_method="weighted",
            db_session=None
        )
        
        avg_hybrid_score = sum(r.hybrid_score for r in results) / len(results) if results else 0
        
        print(f"   Weights V:{vector_weight:.1f}/K:{keyword_weight:.1f} -> Avg Score: {avg_hybrid_score:.3f}")

async def test_cleanup():
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    # Delete test document vectors
    success = await embedding_service.delete_document_chunks(999)
    if success:
        print("✅ Test vectors deleted successfully")
    else:
        print("❌ Failed to delete test vectors")

async def main():
    """Run all hybrid search tests."""
    print("🚀 Starting Hybrid Search Tests\n")
    
    try:
        # Test 1: Keyword Search
        chunks = await test_keyword_search()
        
        # Test 2: Hybrid Search Methods
        doc_id = await test_hybrid_search_methods()
        
        # Test 3: Query Analysis
        await test_query_analysis()
        
        # Test 4: Search Comparison
        await test_search_comparison()
        
        # Test 5: Weight Optimization
        await test_weight_optimization()
        
        # Test 6: Cleanup
        await test_cleanup()
        
        print("\n🎉 All hybrid search tests completed successfully!")
        
        # Summary
        print(f"\n📊 Test Summary:")
        print(f"   - Chunks processed: {len(chunks)}")
        print(f"   - Fusion methods tested: 3 (weighted, RRF, max)")
        print(f"   - Query types analyzed: 6")
        print(f"   - Weight combinations tested: 6")
        print(f"   - Search methods compared: 3")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the tests
    asyncio.run(main()) 
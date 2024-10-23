# LearnAI: Revolutionizing Education with AI

Welcome to LearnAI, an innovative AI-driven educational platform designed to transform the learning experience. Our mission is to provide personalized, adaptive, and engaging education for every student. LearnAI empowers students to learn at their own pace, ensuring that each individual receives the support and resources they need to succeed. By harnessing the power of artificial intelligence, we're creating a future where education is tailored to you. Our platform offers personalized learning paths, performance-based content adjustment, dynamic resource allocation, and a interactive learning elements. Join us on this exciting journey to revolutionize learning!

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

1. **Learner-Aware Content Adaptation**
   - Description: The platform uses questionnaires to assess the learner's learning style and adapts the content accordingly. For example, if the learner is a visual learner, the platform may provide more diagrams and visual aids.
   - Purpose: This feature ensures that learners remain engaged and supported, particularly when they encounter difficult concepts.

2. **Adaptive Learning Paths**
   - Description: The platform dynamically adjusts the difficulty of quizzes and learning materials based on the learner's ongoing performance and progress.
   - Purpose: This personalized approach allows each student to learn at their own pace, promoting a deeper understanding of the material.

3. **AI-Generated Narratives and Explanations**
   - Description: The platform leverages Llama 3.1 and T5 models to generate simplified explanations, engaging narratives, and interactive content from textbook materials.
   - Purpose: By converting complex educational content into more accessible formats, the platform caters to learners with varying levels of proficiency and learning preferences.

4. **Interactive Learning Elements and Real-Time Diagrams**
   - Description: The platform generates interactive learning elements like games and diagrams to help learners understand and remember concepts.
   - Purpose: This feature keeps learners motivated and helps reinforce concepts by providing timely feedback and encouragement.

5. **Inclusivity and Accessibility**
   - Description: The platform is designed to be accessible to all learners, including those with disabilities. Features like text-to-speech, customizable interfaces, and multilingual support ensure that the platform can be used by a diverse audience.
   - Purpose: To create an inclusive learning environment that removes barriers to education, ensuring that everyone has the opportunity to succeed.

## Installation and Setup

To install and setupLearnAI, follow these steps:

1. Clone the repository:
   ```
   git clone https://github.com/manvirchakal/LearnAI
   ```
2. Navigate to the project directory:
   ```
   cd LearnAI
   ```
3. Setup virtual environment:
    ```
    python -m venv venv
    ```
4. Activate the virtual environment:
   - On Windows:
     ```
     .\venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```
     source venv/bin/activate
     ```
   - On Windows with Git Bash:
     ```
     source venv/Scripts/activate
     ```
5. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
6. Install npm packages:
   ```
   cd client
   npm install --legacy-peer-deps
   ```
7. Create a new file called `.env` in the root directory and add the following:
   ```
   AWS_ACCESS_KEY_ID=<your_aws_access_key_id>
   AWS_SECRET_ACCESS_KEY=<your_aws_secret_access_key>
   AWS_DEFAULT_REGION=<your_aws_region>
   COGNITO_AUTHORIZATION_URL=<your_cognito_authorization_url>
   COGNITO_TOKEN_URL=<your_cognito_token_url>
   COGNITO_JWKS_URL=<your_cognito_jwks_url>
   COGNITO_APP_CLIENT_ID=<your_cognito_app_client_id>
   KNOWLEDGE_BASE_ID=<your_knowledge_base_id>
   MODEL_ARN=arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-instant-v1
   TEXTBOOK_S3_BUCKET=<your_textbook_s3_bucket>
   ```
8. Create and `.env.local` file in the client directory and add the following:
   ```
   REACT_APP_AWS_REGION=<your_aws_region>
   REACT_APP_USER_POOL_ID=<your_user_pool_id>
   REACT_APP_USER_POOL_WEB_CLIENT_ID=<your_cognito_app_client_id>
   ```

## Usage

To use LearnAI, follow these steps:

1. To run the server:
   ```
   uvicorn server.main:app --reload
   ```
2. To run the client:
   ```
   cd client
   npm start
   ```
3. Navigate to the URL provided in the client terminal to access the application. (Usually http://localhost:3000)

## Contributing

We welcome contributions to LearnAI! Please follow these steps to contribute:

1. Fork the repository
2. Create a new branch: `git checkout -b feature-branch-name`
3. Make your changes and commit them: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature-branch-name`
5. Submit a pull request

## License

This project is licensed under multiple licenses due to the various components used:

- FastAPI and React components are licensed under the [MIT License](https://opensource.org/licenses/MIT).
- Anthropic Claude is used under the [Anthropic API Terms of Use](https://www.anthropic.com/legal/terms).
- AWS services are used under the [AWS Customer Agreement](https://aws.amazon.com/agreement/).

Please see the [LICENSE.md](LICENSE.md) file for full license texts and any additional details.



import React, { useState } from 'react';
import axios from 'axios';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';

function UploadTextbook() {
    const [file, setFile] = useState(null);
    const navigate = useNavigate();

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        const formData = new FormData();
        formData.append('file', file);

        try {
            const user = await Auth.currentAuthenticatedUser();
            const token = (await Auth.currentSession()).getIdToken().getJwtToken();

            const response = await axios.post('http://localhost:8000/upload', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Bearer ${token}`
                }
            });
            console.log('File uploaded successfully:', response.data);
            // Redirect to study page or show success message
            navigate('/study');
        } catch (error) {
            console.error('Error uploading file:', error);
            if (error.response && error.response.status === 401) {
                // Redirect to login page if unauthorized
                navigate('/login');
            }
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <input type="file" accept=".tex" onChange={handleFileChange} />
            <button type="submit">Upload Textbook</button>
        </form>
    );
}

export default UploadTextbook;

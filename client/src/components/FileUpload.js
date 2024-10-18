import React, { useState } from 'react';
import axios from 'axios';
import { Auth } from 'aws-amplify';
import { useNavigate } from 'react-router-dom';

function UploadTextbook() {
    const [file, setFile] = useState(null);
    const [documentType, setDocumentType] = useState('textbook'); // Changed default to 'textbook'
    const [tocPages, setTocPages] = useState('');
    const navigate = useNavigate();

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleDocumentTypeChange = (event) => {
        setDocumentType(event.target.value);
    };

    const handleTocPagesChange = (event) => {
        setTocPages(event.target.value);
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        const formData = new FormData();
        formData.append('file', file);
        formData.append('documentType', documentType);
        if (documentType === 'textbook') {
            formData.append('tocPages', tocPages);
        }

        try {
            const user = await Auth.currentAuthenticatedUser();
            const token = (await Auth.currentSession()).getIdToken().getJwtToken();

            const response = await axios.post('http://localhost:8000/upload-pdf', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Bearer ${token}`
                }
            });
            console.log('File uploaded successfully:', response.data);
            navigate('/select-textbook');
        } catch (error) {
            console.error('Error uploading file:', error);
            if (error.response && error.response.status === 401) {
                navigate('/login');
            }
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <select value={documentType} onChange={handleDocumentTypeChange}>
                <option value="textbook">Textbook</option>
                <option value="document">Document</option>
            </select>
            <input type="file" accept=".pdf" onChange={handleFileChange} />
            {documentType === 'textbook' && (
                <input
                    type="text"
                    placeholder="Table of Contents pages (e.g., 1-3)"
                    value={tocPages}
                    onChange={handleTocPagesChange}
                />
            )}
            <button type="submit">Upload {documentType === 'textbook' ? 'Textbook' : 'Document'}</button>
        </form>
    );
}

export default UploadTextbook;

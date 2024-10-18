import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Auth } from 'aws-amplify';

function UserBooks() {
    const [books, setBooks] = useState([]);

    useEffect(() => {
        fetchBooks();
    }, []);

    const fetchBooks = async () => {
        try {
            const user = await Auth.currentAuthenticatedUser();
            const token = (await Auth.currentSession()).getIdToken().getJwtToken();

            const response = await axios.get('http://localhost:8000/user-books', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            setBooks(response.data);
        } catch (error) {
            console.error('Error fetching books:', error);
        }
    };

    const downloadBook = async (bookId) => {
        try {
            const user = await Auth.currentAuthenticatedUser();
            const token = (await Auth.currentSession()).getIdToken().getJwtToken();

            const response = await axios.get(`http://localhost:8000/download-book/${bookId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                responseType: 'blob'
            });

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'book.pdf');
            document.body.appendChild(link);
            link.click();
        } catch (error) {
            console.error('Error downloading book:', error);
        }
    };

    return (
        <div>
            <h2>Your Books</h2>
            <ul>
                {books.map(book => (
                    <li key={book.id}>
                        {book.title}
                        <button onClick={() => downloadBook(book.id)}>Download</button>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default UserBooks;

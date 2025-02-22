import React, { useState } from 'react';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';
import './Upload.css';

const Upload = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isLectureModalOpen, setIsLectureModalOpen] = useState(false);
  const [isPowerPointModalOpen, setIsPowerPointModalOpen] = useState(false);
  const [isNotesModalOpen, setIsNotesModalOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [pageRange, setPageRange] = useState('');
  const [lectureTitle, setLectureTitle] = useState('');
  const [powerPointTitle, setPowerPointTitle] = useState('');
  const [notesTitle, setNotesTitle] = useState('');
  const [isTextbook, setIsTextbook] = useState(true);
  const navigate = useNavigate();

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleSubmit = () => {
    console.log('File:', file);
    console.log('Page Range:', pageRange);
    setIsModalOpen(false);
  };

  const handleLectureSubmit = () => {
    console.log('Lecture Title:', lectureTitle);
    console.log('Lecture File:', file);
    setIsLectureModalOpen(false);
  };

  const handlePowerPointSubmit = () => {
    console.log('PowerPoint Title:', powerPointTitle);
    console.log('PowerPoint File:', file);
    setIsPowerPointModalOpen(false);
  };

  const handleNotesSubmit = () => {
    console.log('Notes Title:', notesTitle);
    console.log('Notes File:', file);
    setIsNotesModalOpen(false);
  };

  return (
    <div className="upload-page">
      <NavBar />
      <div className="upload-content">
        <h1>Upload Your Materials</h1>
        <div className="upload-buttons">
          <div className="upload-card" onClick={() => setIsModalOpen(true)}>
            <h3>Upload Textbook</h3>
          </div>
          <div className="upload-card" onClick={() => setIsLectureModalOpen(true)}>
            <h3>Upload Lecture</h3>
          </div>
          <div className="upload-card" onClick={() => setIsPowerPointModalOpen(true)}>
            <h3>Upload PowerPoint</h3>
          </div>
          <div className="upload-card" onClick={() => setIsNotesModalOpen(true)}>
            <h3>Upload Notes</h3>
          </div>
        </div>
        <button className="create-collection-btn">Create a collection</button>
      </div>

      {isModalOpen && (
        <div className="modal">
          <div className="modal-content">
            <h2>Upload {isTextbook ? 'Textbook' : 'Non-Textbook'}</h2>
            <label>
              <input
                type="radio"
                checked={isTextbook}
                onChange={() => setIsTextbook(true)}
              />
              Upload Textbook
            </label>
            <label>
              <input
                type="radio"
                checked={!isTextbook}
                onChange={() => setIsTextbook(false)}
              />
              Upload Non-Textbook PDFs
            </label>
            <label>
              Choose File:
              <input type="file" onChange={handleFileChange} />
            </label>
            {isTextbook && (
              <label>
                Table of Contents Page Range:
                <input
                  type="text"
                  value={pageRange}
                  onChange={(e) => setPageRange(e.target.value)}
                  placeholder="e.g., 1-10"
                />
              </label>
            )}
            <button onClick={handleSubmit}>Submit</button>
            <button onClick={() => setIsModalOpen(false)}>Cancel</button>
          </div>
        </div>
      )}

      {isLectureModalOpen && (
        <div className="modal">
          <div className="modal-content">
            <h2>Upload Lecture</h2>
            <label>
              Lecture Title:
              <input
                type="text"
                value={lectureTitle}
                onChange={(e) => setLectureTitle(e.target.value)}
                placeholder="Enter lecture title"
              />
            </label>
            <label>
              Upload Media:
              <input type="file" onChange={handleFileChange} />
              <p>(.mp3, .mp4, .m4a, .wav files only)</p>
            </label>
            <button onClick={handleLectureSubmit}>Submit</button>
            <button onClick={() => setIsLectureModalOpen(false)}>Cancel</button>
          </div>
        </div>
      )}

      {isPowerPointModalOpen && (
        <div className="modal">
          <div className="modal-content">
            <h2>Upload PowerPoint</h2>
            <label>
              PowerPoint Title:
              <input
                type="text"
                value={powerPointTitle}
                onChange={(e) => setPowerPointTitle(e.target.value)}
                placeholder="Enter PowerPoint title"
              />
            </label>
            <label>
              Upload PowerPoint:
              <input type="file" onChange={handleFileChange} />
              <p>(.ppt, .pptx files only)</p>
            </label>
            <button onClick={handlePowerPointSubmit}>Submit</button>
            <button onClick={() => setIsPowerPointModalOpen(false)}>Cancel</button>
          </div>
        </div>
      )}

      {isNotesModalOpen && (
        <div className="modal">
          <div className="modal-content">
            <h2>Upload Notes</h2>
            <label>
              Notes Title:
              <input
                type="text"
                value={notesTitle}
                onChange={(e) => setNotesTitle(e.target.value)}
                placeholder="Enter notes title"
              />
            </label>
            <label>
              Upload Notes:
              <input type="file" onChange={handleFileChange} />
              <p>(.jpg, .jpeg, .png files only)</p>
            </label>
            <button onClick={handleNotesSubmit}>Submit</button>
            <button onClick={() => setIsNotesModalOpen(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Upload;

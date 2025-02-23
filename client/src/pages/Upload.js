import React, { useState } from 'react';
import NavBar from './NavBar';
import { useNavigate } from 'react-router-dom';
import { 
  FaBook, 
  FaVideo, 
  FaFilePowerpoint, 
  FaFileAlt, 
  FaTimes, 
  FaUpload, 
  FaFolderPlus 
} from 'react-icons/fa';
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

  // Modal component for reuse across different upload types.
  const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
      <div className="modal" onClick={onClose}>
        <div className="modal-content-new" onClick={e => e.stopPropagation()}>
          <div className="modal-header">
            <h2>{title}</h2>
            <button className="close-button" onClick={onClose}>
              <FaTimes size={20} />
            </button>
          </div>
          {children}
        </div>
      </div>
    );
  };

  return (
    <>
      <NavBar />
      <div className="upload-page">
        <div className="upload-content">
          <h1 className="upload-title">Upload Your Materials</h1>
          <div className="upload-grid">
            <div className="upload-card-new" onClick={() => setIsModalOpen(true)}>
              <div className="icon-container">
                <FaBook size={32} />
              </div>
              <h3>Upload Textbook</h3>
            </div>
            <div className="upload-card-new" onClick={() => setIsLectureModalOpen(true)}>
              <div className="icon-container">
                <FaVideo size={32} />
              </div>
              <h3>Upload Lecture</h3>
            </div>
            <div className="upload-card-new" onClick={() => setIsPowerPointModalOpen(true)}>
              <div className="icon-container">
                <FaFilePowerpoint size={32} />
              </div>
              <h3>Upload PowerPoint</h3>
            </div>
            <div className="upload-card-new" onClick={() => setIsNotesModalOpen(true)}>
              <div className="icon-container">
                <FaFileAlt size={32} />
              </div>
              <h3>Upload Notes</h3>
            </div>
          </div>
          <button className="create-collection-btn">
            <FaFolderPlus className="btn-icon" size={20} />
            Create a collection
          </button>
        </div>

        {/* Textbook Modal */}
        <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Upload Textbook">
          <div className="modal-form">
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  checked={isTextbook}
                  onChange={() => setIsTextbook(true)}
                />
                <span>Upload Textbook</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  checked={!isTextbook}
                  onChange={() => setIsTextbook(false)}
                />
                <span>Upload Non-Textbook PDFs</span>
              </label>
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Choose File</span>
                <input type="file" onChange={handleFileChange} className="file-input" />
              </label>
              {file && <p className="file-name">{file.name}</p>}
            </div>
            {isTextbook && (
              <div className="input-group">
                <label>Table of Contents Page Range</label>
                <input
                  type="text"
                  value={pageRange}
                  onChange={(e) => setPageRange(e.target.value)}
                  placeholder="e.g., 1-10"
                  className="text-input"
                />
              </div>
            )}
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* Lecture Modal */}
        <Modal isOpen={isLectureModalOpen} onClose={() => setIsLectureModalOpen(false)} title="Upload Lecture">
          <div className="modal-form">
            <div className="input-group">
              <label>Lecture Title</label>
              <input
                type="text"
                value={lectureTitle}
                onChange={(e) => setLectureTitle(e.target.value)}
                placeholder="Enter lecture title"
                className="text-input"
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload Media</span>
                <input type="file" onChange={handleFileChange} className="file-input" />
              </label>
              {file && <p className="file-name">{file.name}</p>}
              <p className="file-type-hint">(.mp3, .mp4, .m4a, .wav files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsLectureModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleLectureSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* PowerPoint Modal */}
        <Modal isOpen={isPowerPointModalOpen} onClose={() => setIsPowerPointModalOpen(false)} title="Upload PowerPoint">
          <div className="modal-form">
            <div className="input-group">
              <label>PowerPoint Title</label>
              <input
                type="text"
                value={powerPointTitle}
                onChange={(e) => setPowerPointTitle(e.target.value)}
                placeholder="Enter PowerPoint title"
                className="text-input"
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload PowerPoint</span>
                <input type="file" onChange={handleFileChange} className="file-input" />
              </label>
              {file && <p className="file-name">{file.name}</p>}
              <p className="file-type-hint">(.ppt, .pptx files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsPowerPointModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handlePowerPointSubmit}>Submit</button>
            </div>
          </div>
        </Modal>

        {/* Notes Modal */}
        <Modal isOpen={isNotesModalOpen} onClose={() => setIsNotesModalOpen(false)} title="Upload Notes">
          <div className="modal-form">
            <div className="input-group">
              <label>Notes Title</label>
              <input
                type="text"
                value={notesTitle}
                onChange={(e) => setNotesTitle(e.target.value)}
                placeholder="Enter notes title"
                className="text-input"
              />
            </div>
            <div className="file-upload-container">
              <label className="file-input-label">
                <FaUpload size={24} />
                <span>Upload Notes</span>
                <input type="file" onChange={handleFileChange} className="file-input" />
              </label>
              {file && <p className="file-name">{file.name}</p>}
              <p className="file-type-hint">(.jpg, .jpeg, .png files only)</p>
            </div>
            <div className="modal-actions">
              <button className="btn-secondary" onClick={() => setIsNotesModalOpen(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleNotesSubmit}>Submit</button>
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
};

export default Upload;

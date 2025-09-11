import React, { useState } from 'react';
import axios from 'axios';
import './AnalyzePost.css';

const AnalyzePost = ({ setIsLoading, setError, setAnalysisResult, setPostText }) => {
    const [url, setUrl] = useState('');

    const handleAnalyze = async () => {
        if (!url.trim()) {
            setError('Please enter a post URL.');
            return;
        }
        setIsLoading(true);
        setError('');
        setAnalysisResult(null);
        setPostText('');

        try {
            const apiPath = process.env.NODE_ENV === 'production' ? '/api/fetch_and_analyze' : 'https://fluffy-telegram-q74xx7gr9x6w2xwvw-5000.app.github.dev';

            const response = await axios.post(apiPath, { url: url });
            
            setPostText(response.data.postText);
            setAnalysisResult({
                sentiment: response.data.sentiment,
                score: response.data.score
            });

        } catch (err) {
            setError(err.response?.data?.error || 'Failed to analyze the post.');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="card">
            <h2>Analyze a Post</h2>
            <div className="input-group">
                <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Paste X post link here..."
                />
                <button onClick={handleAnalyze}>Analyze</button>
            </div>
        </div>
    );
};

export default AnalyzePost;
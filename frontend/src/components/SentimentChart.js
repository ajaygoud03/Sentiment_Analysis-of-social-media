import React from 'react';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const SentimentChart = ({ result }) => {
    const data = {
        labels: result ? [result.sentiment, 'Other'] : ['N/A'],
        datasets: [
            {
                label: 'Confidence Score',
                data: result ? [result.score, 1 - result.score] : [1],
                backgroundColor: [
                    result?.sentiment === 'Positive' ? '#22a55a' : result?.sentiment === 'Negative' ? '#e13b30' : '#6b7280',
                    '#e5e7eb',
                ],
                borderColor: [
                    '#ffffff',
                    '#ffffff',
                ],
                borderWidth: 2,
            },
        ],
    };

    const options = {
        plugins: {
            legend: {
                display: false,
            },
        },
        cutout: '70%',
    };

    return (
        <div className="card">
            <h2>Visual Analytics</h2>
            <div style={{ maxWidth: '200px', margin: '20px auto' }}>
                <Doughnut data={data} options={options} />
            </div>
            <p style={{ textAlign: 'center', marginTop: '20px' }}>
                {result ? `Confidence score for ${result.sentiment} sentiment.` : 'Chart will be displayed here after analysis.'}
            </p>
        </div>
    );
};

export default SentimentChart;
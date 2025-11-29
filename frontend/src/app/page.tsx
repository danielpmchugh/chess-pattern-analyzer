'use client';

import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

interface AnalysisResult {
  username: string;
  total_games: number;
  patterns: {
    tactical_errors: number;
    opening_mistakes: number;
    time_pressure: number;
    positional_errors: number;
    endgame_mistakes: number;
  };
  recommendations: string[];
  analysis_date: string;
}

export default function Home() {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username.trim()) {
      setError('Please enter a Chess.com username');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/api/v1/analyze/${username}?games_limit=10`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to analyze games');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            Chess Pattern Analyzer
          </h1>
          <p className="text-xl text-slate-300">
            Identify your weaknesses and improve your game
          </p>
        </div>

        {/* Input Form */}
        <div className="bg-white rounded-2xl shadow-2xl p-8 mb-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="username"
                className="block text-sm font-medium text-slate-700 mb-2"
              >
                Chess.com Username
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your Chess.com username"
                className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition text-slate-900"
                disabled={loading}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors shadow-lg disabled:cursor-not-allowed"
            >
              {loading ? 'Analyzing...' : 'Analyze My Games'}
            </button>
          </form>

          {/* Error Message */}
          {error && (
            <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-slate-600">Analyzing your games...</p>
            <p className="text-sm text-slate-400 mt-2">This may take a minute</p>
          </div>
        )}

        {/* Results */}
        {result && !loading && (
          <div className="bg-white rounded-2xl shadow-2xl p-8 space-y-6">
            <div className="border-b border-slate-200 pb-4">
              <h2 className="text-2xl font-bold text-slate-900">
                Analysis Results for {result.username}
              </h2>
              <p className="text-slate-600 text-sm mt-1">
                Based on {result.total_games} recent games
              </p>
            </div>

            {/* Pattern Detection */}
            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-4">
                Detected Patterns
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-red-900">
                      Tactical Errors
                    </span>
                    <span className="text-2xl font-bold text-red-600">
                      {result.patterns.tactical_errors}
                    </span>
                  </div>
                </div>

                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-orange-900">
                      Opening Mistakes
                    </span>
                    <span className="text-2xl font-bold text-orange-600">
                      {result.patterns.opening_mistakes}
                    </span>
                  </div>
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-yellow-900">
                      Time Pressure
                    </span>
                    <span className="text-2xl font-bold text-yellow-600">
                      {result.patterns.time_pressure}
                    </span>
                  </div>
                </div>

                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-purple-900">
                      Positional Errors
                    </span>
                    <span className="text-2xl font-bold text-purple-600">
                      {result.patterns.positional_errors}
                    </span>
                  </div>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 md:col-span-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-blue-900">
                      Endgame Mistakes
                    </span>
                    <span className="text-2xl font-bold text-blue-600">
                      {result.patterns.endgame_mistakes}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recommendations */}
            {result.recommendations && result.recommendations.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-slate-900 mb-4">
                  Recommendations
                </h3>
                <ul className="space-y-3">
                  {result.recommendations.map((rec, index) => (
                    <li key={index} className="flex items-start">
                      <span className="flex-shrink-0 h-6 w-6 rounded-full bg-green-100 text-green-600 flex items-center justify-center text-sm font-medium mr-3">
                        {index + 1}
                      </span>
                      <span className="text-slate-700">{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Analysis Date */}
            <div className="text-center text-sm text-slate-500 pt-4 border-t border-slate-200">
              Analysis completed on {new Date(result.analysis_date).toLocaleString()}
            </div>
          </div>
        )}

        {/* Footer Info */}
        <div className="mt-12 text-center text-slate-400 text-sm">
          <p>Powered by Stockfish Chess Engine</p>
          <p className="mt-2">Data from Chess.com Published-Data API</p>
        </div>
      </div>
    </div>
  );
}

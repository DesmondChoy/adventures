import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Award, 
  BookOpen, 
  Brain,
  ChevronDown, 
  Clock, 
  MapPin, 
  PartyPopper, 
  Sparkles, 
  Trophy 
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';

import Confetti from '@/components/adventure/Confetti';
import ChapterCard from '@/components/adventure/ChapterCard';
import EducationalCard from '@/components/adventure/EducationalCard';
import StatisticCard from '@/components/adventure/StatisticCard';
import { QuestionData } from '@/components/adventure/EducationalCard';
import { AdventureSummaryData } from '@/lib/types';

// No default data - we'll only use real data from the API

const AdventureSummary: React.FC = () => {
  const [showConfetti, setShowConfetti] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [summaryData, setSummaryData] = useState<AdventureSummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Trigger confetti animation when component mounts
    setShowConfetti(true);
    
    // Delay the appearance of content for a better visual effect
    const timer = setTimeout(() => {
      setContentVisible(true);
    }, 800);
    
    // Fetch the summary data
    const fetchData = async () => {
      try {
        // Try to fetch from the API endpoint
        const response = await fetch('/adventure/api/adventure-summary');
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        setSummaryData(data);
      } catch (err) {
        console.error('Error fetching summary data:', err);
        const errorMessage = err instanceof Error ? err.message : String(err);
        setError(errorMessage);
        // No fallback to default data - we'll show an error message instead
      } finally {
        setLoading(false);
      }
    };
    
    fetchData();
    
    return () => clearTimeout(timer);
  }, []);

  // If still loading, show a loading indicator
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-odyssey-blue border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your adventure summary...</p>
        </div>
      </div>
    );
  }

  // If there's an error, show an appropriate message
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 flex items-center justify-center">
        <div className="text-center max-w-md p-6 bg-white rounded-xl shadow-md">
          <div className="text-amber-500 mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold mb-2">No Adventure Found</h2>
          <p className="text-gray-600 mb-4">
            {error.includes("404") 
              ? "You need to complete an adventure before viewing the summary." 
              : error.includes("400")
                ? "Your adventure is not complete. Please finish all chapters to view the summary."
                : `Error loading data: ${error}`}
          </p>
          <Button variant="outline">
            <Link to="/">Start an Adventure</Link>
          </Button>
        </div>
      </div>
    );
  }

  // If we have data, render the summary
  const data = summaryData!; // Use non-null assertion since we've already checked for errors

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50 overflow-hidden">
      {showConfetti && <Confetti count={100} duration={5000} />}
      
      <div className="container mx-auto px-4 py-16 max-w-5xl">
        {/* Header Section */}
        <div className={`text-center mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="inline-block animate-float mb-4">
            <div className="bg-white rounded-full p-4 shadow-md">
              <PartyPopper className="h-12 w-12 text-odyssey-pink" />
            </div>
          </div>
          
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-odyssey-blue via-odyssey-purple to-odyssey-pink">
            Adventure Complete!
          </h1>
          
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Congratulations on completing your learning odyssey! Let's revisit your journey and celebrate all that you've learned.
          </p>
        </div>
        
        {/* Statistics Section */}
        <div className={`grid grid-cols-1 md:grid-cols-3 gap-4 mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <StatisticCard 
            title="Chapters Completed" 
            value={data.statistics.chaptersCompleted.toString()} 
            icon={<BookOpen className="h-6 w-6 text-odyssey-blue" />}
            delay={200}
          />
          <StatisticCard 
            title="Questions Answered" 
            value={data.statistics.questionsAnswered.toString()} 
            icon={<Brain className="h-6 w-6 text-odyssey-purple" />}
            delay={400}
          />
          <StatisticCard 
            title="Time Spent" 
            value={data.statistics.timeSpent} 
            icon={<Clock className="h-6 w-6 text-odyssey-pink" />}
            delay={600}
          />
        </div>
        
        {/* Achievement Badge */}
        <Card className={`p-6 mb-12 glass-card text-center transition-opacity duration-700 ${contentVisible ? 'opacity-100' : 'opacity-0'}`}>
          <div className="flex justify-center mb-4">
            <div className="achievement-badge h-24 w-24 animate-pulse-soft">
              <Trophy className="h-12 w-12 text-white z-10 relative" />
            </div>
          </div>
          
          <h2 className="text-2xl font-bold mb-2">Adventure Master</h2>
          <p className="text-gray-600 mb-4">You've demonstrated curiosity, problem-solving, and a love for learning!</p>
          
          <div className="flex justify-center space-x-2">
            <div className="bg-odyssey-teal/10 text-odyssey-teal text-sm font-medium rounded-full px-3 py-1">
              Creative Thinker
            </div>
            <div className="bg-odyssey-purple/10 text-odyssey-purple text-sm font-medium rounded-full px-3 py-1">
              Knowledge Seeker
            </div>
            <div className="bg-odyssey-pink/10 text-odyssey-pink text-sm font-medium rounded-full px-3 py-1">
              Problem Solver
            </div>
          </div>
        </Card>
        
        {/* Journey Timeline Section */}
        <div className={`mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-300' : 'opacity-0'}`}>
          <div className="flex items-center mb-6">
            <MapPin className="h-6 w-6 text-odyssey-teal mr-2" />
            <h2 className="text-2xl font-bold">Your Adventure Journey</h2>
          </div>
          
          <div className="relative pl-4">
            <div className="timeline-connector" />
            
            {data.chapterSummaries.map((chapter, index) => (
              <ChapterCard 
                key={chapter.number}
                number={chapter.number}
                title={chapter.title}
                summary={chapter.summary}
                delay={index * 150}
              />
            ))}
          </div>
        </div>
        
        {/* Educational Achievement Section */}
        <div className={`mb-12 transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-500' : 'opacity-0'}`}>
          <div className="flex items-center mb-6">
            <Sparkles className="h-6 w-6 text-odyssey-lavender mr-2" />
            <h2 className="text-2xl font-bold">Knowledge Gained</h2>
          </div>
          
          <div className="grid grid-cols-1 gap-6">
            {data.educationalQuestions.map((question, index) => (
              <EducationalCard 
                key={index}
                data={question}
                index={index}
                delay={index * 200}
              />
            ))}
          </div>
        </div>
        
        {/* Footer Section */}
        <div className={`text-center transition-opacity duration-700 ${contentVisible ? 'opacity-100 delay-700' : 'opacity-0'}`}>
          <Separator className="mb-8" />
          
          <div className="mb-6">
            <Award className="h-8 w-8 text-odyssey-yellow mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Ready for Another Adventure?</h2>
            <p className="text-gray-600 mb-6">
              Your curiosity has led you through an amazing journey. What will you discover next?
            </p>
          </div>
          
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Button 
              size="lg" 
              className="bg-gradient-to-r from-odyssey-blue to-odyssey-teal hover:opacity-90 transition-opacity"
            >
              <Link to="/">Start New Adventure</Link>
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              className="border-odyssey-purple text-odyssey-purple hover:bg-odyssey-purple/5"
            >
              <Link to="/">Return Home</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdventureSummary;

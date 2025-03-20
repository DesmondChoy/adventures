
import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Award, Sparkles, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

const Index = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-purple-50">
      <div className="container mx-auto px-4 py-16 max-w-5xl">
        <header className="text-center mb-16 animate-fade-in">
          <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-clip-text text-transparent bg-gradient-to-r from-odyssey-blue via-odyssey-purple to-odyssey-pink">
            Learning Odyssey
          </h1>
          <p className="text-gray-600 text-lg max-w-2xl mx-auto">
            Embark on an educational adventure through interactive stories and challenges
          </p>
        </header>

        <div className="grid md:grid-cols-2 gap-8 mb-16">
          <Card className="p-8 glass-card animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="mb-4 rounded-full bg-odyssey-blue/10 w-12 h-12 flex items-center justify-center">
              <BookOpen className="h-6 w-6 text-odyssey-blue" />
            </div>
            <h2 className="text-2xl font-bold mb-3">Interactive Stories</h2>
            <p className="text-gray-600 mb-6">
              Dive into engaging narratives where your choices shape the outcome. Each story combines
              entertainment with educational content.
            </p>
            <Button variant="outline" className="group">
              Browse Stories
              <ChevronRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </Card>

          <Card className="p-8 glass-card animate-fade-in-up" style={{ animationDelay: '400ms' }}>
            <div className="mb-4 rounded-full bg-odyssey-purple/10 w-12 h-12 flex items-center justify-center">
              <Award className="h-6 w-6 text-odyssey-purple" />
            </div>
            <h2 className="text-2xl font-bold mb-3">Learn Through Play</h2>
            <p className="text-gray-600 mb-6">
              Educational content is seamlessly woven into each adventure, making learning natural
              and fun for curious minds.
            </p>
            <Button variant="outline" className="group">
              How It Works
              <ChevronRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </Card>
        </div>

        <div className="glass-card p-8 rounded-xl mb-16 animate-fade-in-up" style={{ animationDelay: '600ms' }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="rounded-full bg-odyssey-pink/10 w-12 h-12 flex items-center justify-center">
              <Sparkles className="h-6 w-6 text-odyssey-pink" />
            </div>
            <h2 className="text-2xl font-bold">Featured Adventure</h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <h3 className="text-xl font-semibold mb-2">The Mysterious Carnival</h3>
              <p className="text-gray-600 mb-4">
                Join Leo on a magical journey through the Twisting Tumble Tents carnival, where science, history, and 
                mathematics come alive through enchanting encounters and mind-bending puzzles.
              </p>
              <div className="flex flex-wrap gap-2 mb-6">
                <span className="bg-odyssey-blue/10 text-odyssey-blue text-xs font-medium rounded-full px-2.5 py-1">
                  Ages 8-12
                </span>
                <span className="bg-odyssey-purple/10 text-odyssey-purple text-xs font-medium rounded-full px-2.5 py-1">
                  Science
                </span>
                <span className="bg-odyssey-teal/10 text-odyssey-teal text-xs font-medium rounded-full px-2.5 py-1">
                  History
                </span>
                <span className="bg-odyssey-pink/10 text-odyssey-pink text-xs font-medium rounded-full px-2.5 py-1">
                  Mathematics
                </span>
              </div>
              <div className="flex gap-3">
                <Button className="bg-odyssey-purple hover:bg-odyssey-purple/90">
                  Start Adventure
                </Button>
                <Link to="/adventure-summary">
                  <Button variant="outline" className="border-odyssey-purple text-odyssey-purple hover:bg-odyssey-purple/5">
                    View Summary
                  </Button>
                </Link>
              </div>
            </div>
            <div className="relative h-64 md:h-full rounded-xl overflow-hidden bg-gradient-to-br from-blue-100 to-purple-100">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-odyssey-purple/30 text-lg font-medium">Adventure Preview</div>
              </div>
            </div>
          </div>
        </div>

        <footer className="text-center text-gray-500 text-sm animate-fade-in">
          <p>© 2023 Learning Odyssey. All educational adventures await!</p>
        </footer>
      </div>
    </div>
  );
};

export default Index;

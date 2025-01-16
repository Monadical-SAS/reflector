"use client";
import { useEffect, useState } from 'react';
import Link from 'next/link';

export default function WebinarPage() {
  const [countdown, setCountdown] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0
  });

  useEffect(() => {
    const targetDate = new Date('2024-02-05T18:00:00Z'); // 12pm CST

    const updateCountdown = () => {
      const now = new Date();
      const difference = targetDate.getTime() - now.getTime();

      setCountdown({
        days: Math.floor(difference / (1000 * 60 * 60 * 24)),
        hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
        minutes: Math.floor((difference / 1000 / 60) % 60),
        seconds: Math.floor((difference / 1000) % 60)
      });
    };

    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 bg-gray-50">
      <div className="bg-white rounded-3xl p-8 md:p-12 shadow-md mx-auto" style={{ width: '100%', paddingLeft: '20%', paddingRight: '20%' }}>
        <div className="text-center font-bold text-3xl mb-8">M</div>
        <div className="text-center text-sky-600 text-sm font-semibold mb-4">FREE WEBINAR</div>

        <h1 className="text-center text-4xl md:text-5xl font-bold mb-4 leading-tight">
          Building AI-Powered<br />Operational Assistants
        </h1>

        <p className="text-center text-gray-600 mb-6">
          From Simple Automation to Strategic Implementation
        </p>

        <p className="text-center font-semibold mb-8">
          Wednesday, February 5th @ 12pm CST
        </p>

        <div className="flex justify-center gap-8 mb-8">
          {[
            { value: countdown.days, label: 'DAYS' },
            { value: countdown.hours, label: 'HOURS' },
            { value: countdown.minutes, label: 'MINUTES' },
            { value: countdown.seconds, label: 'SECONDS' }
          ].map((item, index) => (
            <div key={index} className="text-center">
              <div className="text-4xl font-bold mb-2">{item.value}</div>
              <div className="text-sky-600 text-xs font-semibold">{item.label}</div>
            </div>
          ))}
        </div>

        <Link
          href="#"
          className="block w-full max-w-md mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-lg hover:bg-sky-700 transition-colors mb-8"
        >
          RSVP HERE
        </Link>

        <div className="space-y-4 mb-8">
          <p>
            The hype around AI agents might be a little premature.
            But operational assistants are very real, available today, and can unlock your team to do their best work.
          </p>
          <p>
            In this session, Monadical cofounder Max McCrea will dive into what operational assistants are
            and how you can implement them in your organization to deliver real, tangible value.
          </p>
        </div>

        <div className="mb-8">
          <h2 className="font-bold text-xl mb-4">What We'll Cover:</h2>
          <ul className="space-y-4">
            {[
              "What an AI operational consultant is (and isn't).",
              "Example use cases for how they can be implemented across your organization.",
              "Key security and design considerations to avoid sharing sensitive data with outside platforms.",
              "Live demos showing both entry-level and advanced implementations.",
              "How you can start implementing them to immediately unlock value."
            ].map((item, index) => (
              <li key={index} className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600 before:rounded-full">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="mb-8">
          <h2 className="font-bold text-xl mb-4">Who Should Attend:</h2>
          <ul className="space-y-4">
            {[
              "Operations leaders looking to reduce manual work",
              "Technical decision makers evaluating AI solutions",
              "Teams concerned about data security and control"
            ].map((item, index) => (
              <li key={index} className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600 before:rounded-full">
                {item}
              </li>
            ))}
          </ul>
        </div>

        <p className="mb-8">
          Plan to walk away with a clear understanding of how to implement AI solutions in your organization,
          with live demos of actual implementations and plenty of time for Q&A to address your specific challenges.
        </p>

        <Link
          href="#"
          className="block w-full max-w-md mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-lg hover:bg-sky-700 transition-colors mb-8"
        >
          RSVP HERE
        </Link>

        <div className="text-center text-gray-600 text-sm">
          POWERED BY:<br />
          Reflector
        </div>
      </div>
    </div>
  );
}

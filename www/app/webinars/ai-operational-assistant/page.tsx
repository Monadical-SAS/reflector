"use client";
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function WebinarPage() {
  const [countdown, setCountdown] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0
  });

  useEffect(() => {
    const targetDate = new Date('2025-02-05T18:00:00Z'); // 12pm CST

    const updateCountdown = () => {
      const now = new Date();
      const difference = targetDate.getTime() - now.getTime();
      // If the target date has passed, show all zeros
      if (difference < 0) {
        setCountdown({
          days: 0,
          hours: 0,
          minutes: 0,
          seconds: 0
        });
        return;
      }

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
    <div className="max-w-4xl mx-auto px-2 py-8 bg-gray-50">
      <div className="bg-white rounded-3xl px-4 md:px-36 py-4 shadow-md mx-auto">
        <img src="/monadical-black-white 1.svg" alt="Monadical Logo" className="mx-auto mb-8" width={40} height={40} />
        <div className="text-center text-sky-600 text-sm font-semibold mb-4">FREE WEBINAR</div>

        <h1 className="text-center text-4xl md:text-5xl mb-3 leading-tight">
          Building AI-Powered<br />Operational Assistants
        </h1>

        <p className="text-center text-gray-600 mb-4">
          From Simple Automation to Strategic Implementation
        </p>

        <p className="text-center font-semibold mb-4">
          Wednesday, February 5th @ 12pm CST
        </p>

        <div className="flex justify-center gap-1 md:gap-8 mb-8">
          {[
            { value: countdown.days, label: 'DAYS' },
            { value: countdown.hours, label: 'HOURS' },
            { value: countdown.minutes, label: 'MINUTES' },
            { value: countdown.seconds, label: 'SECONDS' }
          ].map((item, index) => (
            <div key={index} className="text-center bg-white border border-gray-100 shadow-md rounded-lg p-4 aspect-square w-24">
              <div className="text-5xl mb-2">{item.value}</div>
              <div className="text-sky-600 text-xs">{item.label}</div>
            </div>
          ))}
        </div>

        <div className="px-6 md:px-16">
            <Link
            href="#"
            className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors mb-8"
            >
            RSVP HERE
            </Link>

            <div className="space-y-4 mb-8 mt-24">
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
                <li key={index} className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600">
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
                <li key={index} className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600">
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
            className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors mb-8"
            >
            RSVP HERE
            </Link>
        </div>
        <div className="text-center text-gray-600 text-sm my-24">
          POWERED BY:<br />
          <Link href="/" className="flex justify-center items-center mx-auto">
            <Image
                src="/reach.svg"
                width={32}
                height={40}
                className="h-11 w-auto"
                alt="Reflector"
            />
            <div className="flex-col ml-3 mt-4">
                <h1 className="text-[28px] font-semibold leading-tight text-left">
                Reflector
                </h1>
                <p className="text-gray-500 text-xs tracking-tight -mt-1">
                Capture the signal, not the noise
                </p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
}

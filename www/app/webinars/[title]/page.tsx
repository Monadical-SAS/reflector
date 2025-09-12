"use client";
import { useEffect, useState, use } from "react";
import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import useRoomMeeting from "../../[roomName]/useRoomMeeting";
import dynamic from "next/dynamic";
const WherebyEmbed = dynamic(() => import("../../lib/WherebyWebinarEmbed"), {
  ssr: false,
});
import { FormEvent } from "react";
import { Input, Field } from "@chakra-ui/react";
import { VStack } from "@chakra-ui/react";
import { Alert } from "@chakra-ui/react";
import { Text } from "@chakra-ui/react";

type FormData = {
  name: string;
  email: string;
  company: string;
  role: string;
};

const FORM_ID = "1hhtO6x9XacRwSZS-HRBLN9Ca_7iGZVpNX3_EC4I1uzc";
const FORM_FIELDS = {
  name: "entry.1500809875",
  email: "entry.1359095250",
  company: "entry.1851914159",
  role: "entry.1022377935",
};

export type WebinarDetails = {
  params: Promise<{
    title: string;
  }>;
};

export type Webinar = {
  title: string;
  startsAt: string;
  endsAt: string;
};

enum WebinarStatus {
  Upcoming = "upcoming",
  Live = "live",
  Ended = "ended",
}

const ROOM_NAME = "webinar";

const WEBINARS: Webinar[] = [
  {
    title: "ai-operational-assistant",
    startsAt: "2025-02-05T17:00:00Z", // 12pm EST
    endsAt: "2025-02-05T18:00:00Z",
  },
  {
    title: "ai-operational-assistant-dry-run",
    startsAt: "2025-02-05T02:30:00Z",
    endsAt: "2025-02-05T03:10:00Z",
  },
];

export default function WebinarPage(details: WebinarDetails) {
  const params = use(details.params);
  const title = params.title;
  const webinar = WEBINARS.find((webinar) => webinar.title === title);
  if (!webinar) {
    return notFound();
  }
  const startDate = new Date(Date.parse(webinar.startsAt));
  const endDate = new Date(Date.parse(webinar.endsAt));

  const meeting = useRoomMeeting(ROOM_NAME);
  const roomUrl = meeting?.response?.host_room_url
    ? meeting?.response?.host_room_url
    : meeting?.response?.room_url;

  const [status, setStatus] = useState(WebinarStatus.Ended);
  const [countdown, setCountdown] = useState({
    days: 0,
    hours: 0,
    minutes: 0,
    seconds: 0,
  });

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date();

      if (now < startDate) {
        setStatus(WebinarStatus.Upcoming);
        const difference = startDate.getTime() - now.getTime();
        setCountdown({
          days: Math.floor(difference / (1000 * 60 * 60 * 24)),
          hours: Math.floor((difference / (1000 * 60 * 60)) % 24),
          minutes: Math.floor((difference / 1000 / 60) % 60),
          seconds: Math.floor((difference / 1000) % 60),
        });
      } else if (now < endDate) {
        setStatus(WebinarStatus.Live);
      }
    };

    updateCountdown();

    const timer = setInterval(updateCountdown, 1000);
    return () => clearInterval(timer);
  }, [webinar]);

  const [formSubmitted, setFormSubmitted] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    name: "",
    email: "",
    company: "",
    role: "",
  });

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    try {
      const submitUrl = `https://docs.google.com/forms/d/${FORM_ID}/formResponse`;
      const data = Object.entries(FORM_FIELDS)
        .map(([key, value]) => {
          return `${value}=${formData[key as keyof FormData]}`;
        })
        .join("&");
      const response = await fetch(submitUrl, {
        method: "POST",
        mode: "no-cors",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: data,
      });

      setFormSubmitted(true);
    } catch (error) {
      console.error("Error submitting form:", error);
    }
  };

  const handleLeave = () => {
    const now = new Date();
    if (now > endDate) {
      window.location.reload();
    }
  };

  if (status === WebinarStatus.Live) {
    return (
      <>{roomUrl && <WherebyEmbed roomUrl={roomUrl} onLeave={handleLeave} />}</>
    );
  }
  if (status === WebinarStatus.Ended) {
    return (
      <div className="max-w-4xl mx-auto px-2 py-8 bg-gray-50">
        <div className="bg-white rounded-3xl px-4 md:px-36 py-4 shadow-md mx-auto">
          <Link href="https://www.monadical.com" target="_blank">
            <img
              src="/monadical-black-white 1.svg"
              alt="Monadical Logo"
              className="mx-auto mb-8"
              width={40}
              height={40}
            />
          </Link>
          <div className="text-center text-sky-600 text-sm font-semibold mb-4">
            FREE RECORDING
          </div>

          <h1 className="text-center text-4xl md:text-5xl mb-3 leading-tight">
            Building AI-Powered
            <br />
            Operational Assistants
          </h1>

          <p className="text-center text-gray-600 mb-4">
            From Simple Automation to Strategic Implementation
          </p>

          <Image
            src="/webinar-preview.png"
            alt="Webinar Preview"
            width={1280}
            height={720}
            className="mx-auto mb-8"
            style={{
              borderRadius: "12px",
              boxShadow: "0px 4px 12px 0px rgba(0, 0, 0, 0.1)",
            }}
          />

          <div className="px-6 md:px-16">
            <button
              onClick={() =>
                window.scrollTo({
                  top: document.body.scrollHeight,
                  behavior: "smooth",
                })
              }
              className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors mb-8 uppercase"
            >
              Get instant access
            </button>

            <div className="space-y-4 mb-8 mt-24">
              <p>
                The hype around Al agents might be a little premature. But
                operational assistants are very real, available today, and can
                unlock your team to do their best work.
              </p>
              <p>
                In this session,{" "}
                <Link
                  href="https://www.monadical.com"
                  target="_blank"
                  className="text-sky-600 hover:text-sky-700"
                >
                  Monadical
                </Link>{" "}
                cofounder Max McCrea dives into what operational assistants are
                and how you can implement them in your organization to deliver
                real, tangible value.
              </p>
            </div>

            <div className="mb-8">
              <h2 className="font-bold text-xl mb-4">What We Cover:</h2>
              <ul className="space-y-4">
                {[
                  "What an AI operational assistant is (and isn't).",
                  "Example use cases for how they can be implemented across your organization.",
                  "Key security and design considerations to avoid sharing sensitive data with outside platforms.",
                  "Live demos showing both entry-level and advanced implementations.",
                  "How you can start implementing them to immediately unlock value.",
                ].map((item, index) => (
                  <li
                    key={index}
                    className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600"
                  >
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <p className="mb-8">
              You'll walk away with a clear understanding of how to implement Al
              solutions in your organization, with several demos of actual
              implementations.
            </p>

            <div className="mb-8">
              <h2 className="font-bold text-xl mb-4">
                To Watch This Webinar, Fill Out the Brief Form Below:
              </h2>

              {formSubmitted ? (
                <Alert.Root status="success" borderRadius="lg" mb={4}>
                  <Alert.Indicator />
                  <Alert.Title>
                    Thanks for signing up! The webinar recording will be ready
                    soon, and we'll email you as soon as it's available. Stay
                    tuned!
                  </Alert.Title>
                </Alert.Root>
              ) : (
                <form onSubmit={handleSubmit}>
                  <VStack gap={4} w="full">
                    <Field.Root required>
                      <Input
                        type="text"
                        placeholder="Your Name"
                        py={4}
                        size="md"
                        value={formData.name}
                        onChange={(e) =>
                          setFormData({ ...formData, name: e.target.value })
                        }
                      />
                    </Field.Root>
                    <Field.Root required>
                      <Input
                        type="email"
                        placeholder="Your Email"
                        py={4}
                        size="md"
                        value={formData.email}
                        onChange={(e) =>
                          setFormData({ ...formData, email: e.target.value })
                        }
                      />
                    </Field.Root>
                    <Input
                      type="text"
                      placeholder="Company Name"
                      py={4}
                      size="md"
                      value={formData.company}
                      onChange={(e) =>
                        setFormData({ ...formData, company: e.target.value })
                      }
                    />
                    <Input
                      type="text"
                      placeholder="Your Role"
                      py={4}
                      size="md"
                      value={formData.role}
                      onChange={(e) =>
                        setFormData({ ...formData, role: e.target.value })
                      }
                    />
                    <button
                      type="submit"
                      className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors uppercase"
                    >
                      Get instant access
                    </button>
                  </VStack>
                </form>
              )}
            </div>
          </div>
          <div className="text-center text-gray-600 text-sm my-24">
            POWERED BY:
            <br />
            <Link href="#" className="flex justify-center items-center mx-auto">
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

  return (
    <div className="max-w-4xl mx-auto px-2 py-8 bg-gray-50">
      <div className="bg-white rounded-3xl px-4 md:px-36 py-4 shadow-md mx-auto">
        <Link href="https://www.monadical.com" target="_blank">
          <img
            src="/monadical-black-white 1.svg"
            alt="Monadical Logo"
            className="mx-auto mb-8"
            width={40}
            height={40}
          />
        </Link>
        <div className="text-center text-sky-600 text-sm font-semibold mb-4">
          FREE WEBINAR
        </div>

        <h1 className="text-center text-4xl md:text-5xl mb-3 leading-tight">
          Building AI-Powered
          <br />
          Operational Assistants
        </h1>

        <p className="text-center text-gray-600 mb-4">
          From Simple Automation to Strategic Implementation
        </p>

        <p className="text-center font-semibold mb-4">
          Wednesday, February 5th @ 12pm EST
        </p>

        <div className="flex justify-center gap-1 md:gap-8 mb-8">
          {[
            { value: countdown.days, label: "DAYS" },
            { value: countdown.hours, label: "HOURS" },
            { value: countdown.minutes, label: "MINUTES" },
            { value: countdown.seconds, label: "SECONDS" },
          ].map((item, index) => (
            <div
              key={index}
              className="text-center bg-white border border-gray-100 shadow-md rounded-lg p-4 aspect-square w-24"
            >
              <div className="text-5xl mb-2">{item.value}</div>
              <div className="text-sky-600 text-xs">{item.label}</div>
            </div>
          ))}
        </div>

        <div className="px-6 md:px-16">
          <Link
            href="https://www.linkedin.com/events/7286034395642179584/"
            target="_blank"
            className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors mb-8"
          >
            RSVP HERE
          </Link>

          <div className="space-y-4 mb-8 mt-24">
            <p>
              AI is ready to deliver value to your organization, but it's not
              ready to act autonomously. The highest-value applications of AI
              today are assistants, which significantly increase the efficiency
              of workers in operational roles. Software companies are reporting
              30% improvements in developer output across the board, and there's
              no reason AI can't deliver the same kind of value to workers in
              other roles.
            </p>
            <p>
              In this session,{" "}
              <Link
                href="https://www.monadical.com"
                target="_blank"
                className="text-sky-600 hover:text-sky-700"
              >
                Monadical
              </Link>{" "}
              cofounder Max McCrea will dive into what operational assistants
              are and how you can implement them in your organization to deliver
              real, tangible value.
            </p>
          </div>

          <div className="mb-8">
            <h2 className="font-bold text-xl mb-4">What We'll Cover:</h2>
            <ul className="space-y-4">
              {[
                "What an AI operational assistant is (and isn't).",
                "Example use cases for how they can be implemented across your organization.",
                "Key security and design considerations to avoid sharing sensitive data with outside platforms.",
                "Live demos showing both entry-level and advanced implementations.",
                "How you can start implementing them to immediately unlock value.",
              ].map((item, index) => (
                <li
                  key={index}
                  className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600"
                >
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
                "Teams concerned about data security and control",
              ].map((item, index) => (
                <li
                  key={index}
                  className="pl-6 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-sky-600"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <p className="mb-8">
            Plan to walk away with a clear understanding of how to implement AI
            solutions in your organization, with live demos of actual
            implementations and plenty of time for Q&A to address your specific
            challenges.
          </p>

          <Link
            href="https://www.linkedin.com/events/7286034395642179584/"
            target="_blank"
            className="block w-full max-w-xs mx-auto py-4 px-6 bg-sky-600 text-white text-center font-semibold rounded-full hover:bg-sky-700 transition-colors mb-8"
          >
            RSVP HERE
          </Link>
        </div>
        <div className="text-center text-gray-600 text-sm my-24">
          POWERED BY:
          <br />
          <Link href="#" className="flex justify-center items-center mx-auto">
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

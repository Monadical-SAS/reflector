import { Paragraph, Title } from "../lib/textComponents";

export default () => (
  <div className="max-w-xl">
    <Title>Privacy Policy</Title>
    <Paragraph className="italic">Last updated on September 22, 2023</Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">Recording Consent</span>:
      by using Reflector, you grant us permission to record your interactions
      for the purpose of showcasing Reflector's capabilities during the All In
      AI conference.
    </Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">Data Access</span>: you
      will have convenient access to your recorded sessions and transcriptions
      via a unique URL, which remains active for a period of seven days. After
      this time, your recordings and transcripts will be deleted.
    </Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">Data Confidentiality</span>
      : rest assured that none of your audio data will be shared with third
      parties.
    </Paragraph>
    <Paragraph>
      <span className="font-semibold text-slate-100">
        Questions or Concerns
      </span>
      : if you have any questions or concerns regarding your data, please feel
      free to reach out to us at{" "}
      <a href="mailto:reflector@monadical.com" className="underline">
        reflector@monadical.com
      </a>
    </Paragraph>
  </div>
);

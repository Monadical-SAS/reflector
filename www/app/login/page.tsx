"use client";

import { useState } from "react";
import { signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Field,
  Input,
  VStack,
  Text,
  Heading,
} from "@chakra-ui/react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const result = await signIn("credentials", {
      email,
      password,
      redirect: false,
    });

    setLoading(false);

    if (result?.error) {
      console.log(result?.error);
      setError("Invalid email or password");
    } else {
      router.push("/");
    }
  };

  return (
    <Box maxW="400px" mx="auto" mt="100px" p={6}>
      <VStack gap={6} as="form" onSubmit={handleSubmit}>
        <Heading size="lg">Log in</Heading>
        {error && <Text color="red.500">{error}</Text>}
        <Field.Root required>
          <Field.Label>Email</Field.Label>
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field.Root>
        <Field.Root required>
          <Field.Label>Password</Field.Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field.Root>
        <Button
          type="submit"
          colorPalette="blue"
          width="full"
          loading={loading}
        >
          Log in
        </Button>
      </VStack>
    </Box>
  );
}

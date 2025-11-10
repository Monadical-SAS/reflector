"use client";
import React, { useState, useRef } from "react";
import {
  Box,
  Button,
  Heading,
  Stack,
  Text,
  Input,
  Table,
  Flex,
  IconButton,
  Code,
  Dialog,
} from "@chakra-ui/react";
import { LuTrash2, LuCopy, LuPlus } from "react-icons/lu";
import { useQueryClient } from "@tanstack/react-query";
import { $api } from "../../../lib/apiClient";
import { toaster } from "../../../components/ui/toaster";

interface CreateApiKeyResponse {
  id: string;
  user_id: string;
  name: string | null;
  created_at: string;
  key: string;
}

export default function ApiKeysPage() {
  const [newKeyName, setNewKeyName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<CreateApiKeyResponse | null>(
    null,
  );
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Fetch API keys
  const { data: apiKeys, isLoading } = $api.useQuery(
    "get",
    "/v1/user/api-keys",
  );

  // Create API key mutation
  const createKeyMutation = $api.useMutation("post", "/v1/user/api-keys", {
    onSuccess: (data) => {
      setCreatedKey(data as CreateApiKeyResponse);
      setNewKeyName("");
      setIsCreating(false);
      queryClient.invalidateQueries({ queryKey: ["get", "/v1/user/api-keys"] });
      toaster.create({
        duration: 5000,
        render: () => (
          <Box bg="green.500" color="white" px={4} py={3} borderRadius="md">
            <Text fontWeight="bold">API key created</Text>
            <Text fontSize="sm">
              Make sure to copy it now - you won't see it again!
            </Text>
          </Box>
        ),
      });
    },
    onError: () => {
      toaster.create({
        duration: 3000,
        render: () => (
          <Box bg="red.500" color="white" px={4} py={3} borderRadius="md">
            <Text fontWeight="bold">Error</Text>
            <Text fontSize="sm">Failed to create API key</Text>
          </Box>
        ),
      });
    },
  });

  // Delete API key mutation
  const deleteKeyMutation = $api.useMutation(
    "delete",
    "/v1/user/api-keys/{key_id}",
    {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: ["get", "/v1/user/api-keys"],
        });
        toaster.create({
          duration: 3000,
          render: () => (
            <Box bg="green.500" color="white" px={4} py={3} borderRadius="md">
              <Text fontWeight="bold">API key deleted</Text>
            </Box>
          ),
        });
      },
      onError: () => {
        toaster.create({
          duration: 3000,
          render: () => (
            <Box bg="red.500" color="white" px={4} py={3} borderRadius="md">
              <Text fontWeight="bold">Error</Text>
              <Text fontSize="sm">Failed to delete API key</Text>
            </Box>
          ),
        });
      },
    },
  );

  const handleCreateKey = () => {
    createKeyMutation.mutate({
      body: { name: newKeyName || null },
    });
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    toaster.create({
      duration: 2000,
      render: () => (
        <Box bg="green.500" color="white" px={4} py={3} borderRadius="md">
          <Text fontWeight="bold">Copied to clipboard</Text>
        </Box>
      ),
    });
  };

  const handleDeleteRequest = (keyId: string) => {
    setKeyToDelete(keyId);
  };

  const confirmDelete = () => {
    if (keyToDelete) {
      deleteKeyMutation.mutate({
        params: { path: { key_id: keyToDelete } },
      });
      setKeyToDelete(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Box maxW="1200px" mx="auto" p={8}>
      <Heading mb={2}>API Keys</Heading>
      <Text color="gray.600" mb={6}>
        Manage your API keys for programmatic access to Reflector
      </Text>

      {/* Show newly created key */}
      {createdKey && (
        <Box
          mb={6}
          p={4}
          bg="green.50"
          borderWidth={1}
          borderColor="green.200"
          borderRadius="md"
        >
          <Flex justify="space-between" align="start" mb={2}>
            <Heading size="sm" color="green.800">
              API Key Created
            </Heading>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setCreatedKey(null)}
            >
              ×
            </Button>
          </Flex>
          <Text mb={2} fontSize="sm" color="green.700">
            Make sure to copy your API key now. You won't be able to see it
            again!
          </Text>
          <Flex gap={2} align="center">
            <Code p={2} flex={1} fontSize="sm" bg="white">
              {createdKey.key}
            </Code>
            <IconButton
              aria-label="Copy API key"
              size="sm"
              onClick={() => handleCopyKey(createdKey.key)}
            >
              <LuCopy />
            </IconButton>
          </Flex>
        </Box>
      )}

      {/* Create new key */}
      <Box mb={8} p={6} borderWidth={1} borderRadius="md">
        <Heading size="md" mb={4}>
          Create New API Key
        </Heading>
        {!isCreating ? (
          <Button onClick={() => setIsCreating(true)} colorPalette="blue">
            <LuPlus /> Create API Key
          </Button>
        ) : (
          <Stack gap={4}>
            <Box>
              <Text mb={2}>Name (optional)</Text>
              <Input
                placeholder="e.g., Production API Key"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
              />
            </Box>
            <Flex gap={2}>
              <Button
                onClick={handleCreateKey}
                colorPalette="blue"
                loading={createKeyMutation.isPending}
              >
                Create
              </Button>
              <Button
                onClick={() => {
                  setIsCreating(false);
                  setNewKeyName("");
                }}
                variant="outline"
              >
                Cancel
              </Button>
            </Flex>
          </Stack>
        )}
      </Box>

      {/* List of API keys */}
      <Box>
        <Heading size="md" mb={4}>
          Your API Keys
        </Heading>
        {isLoading ? (
          <Text>Loading...</Text>
        ) : !apiKeys || apiKeys.length === 0 ? (
          <Text color="gray.600">
            No API keys yet. Create one to get started.
          </Text>
        ) : (
          <Table.Root>
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeader>Name</Table.ColumnHeader>
                <Table.ColumnHeader>Created</Table.ColumnHeader>
                <Table.ColumnHeader>Actions</Table.ColumnHeader>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {apiKeys.map((key) => (
                <Table.Row key={key.id}>
                  <Table.Cell>
                    {key.name || <Text color="gray.500">Unnamed</Text>}
                  </Table.Cell>
                  <Table.Cell>{formatDate(key.created_at)}</Table.Cell>
                  <Table.Cell>
                    <IconButton
                      aria-label="Delete API key"
                      size="sm"
                      colorPalette="red"
                      variant="ghost"
                      onClick={() => handleDeleteRequest(key.id)}
                      loading={
                        deleteKeyMutation.isPending &&
                        deleteKeyMutation.variables?.params?.path?.key_id ===
                          key.id
                      }
                    >
                      <LuTrash2 />
                    </IconButton>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        )}
      </Box>

      {/* Delete confirmation dialog */}
      <Dialog.Root
        open={!!keyToDelete}
        onOpenChange={(e) => {
          if (!e.open) setKeyToDelete(null);
        }}
        initialFocusEl={() => cancelRef.current}
      >
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header fontSize="lg" fontWeight="bold">
              Delete API Key
            </Dialog.Header>
            <Dialog.Body>
              <Text>
                Are you sure you want to delete this API key? This action cannot
                be undone.
              </Text>
            </Dialog.Body>
            <Dialog.Footer>
              <Button
                ref={cancelRef}
                onClick={() => setKeyToDelete(null)}
                variant="outline"
                colorPalette="gray"
              >
                Cancel
              </Button>
              <Button colorPalette="red" onClick={confirmDelete} ml={3}>
                Delete
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>
    </Box>
  );
}

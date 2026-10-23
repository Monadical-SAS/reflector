import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  CloseButton,
  Dialog,
  Flex,
  IconButton,
  Spinner,
  Stack,
  Text,
} from "@chakra-ui/react";
import { LuDownload } from "react-icons/lu";
import { useTranscriptDownloads } from "../../lib/apiHooks";
import { API_URL } from "../../lib/apiClient";
import { useAuth } from "../../lib/AuthProvider";
import { parseMaybeNonEmptyString } from "../../lib/utils";
import { toaster } from "../../components/ui/toaster";
import {
  buildZipUrl,
  formatSize,
  groupDownloads,
  resolveDownloadUrl,
  startDownload,
  type DownloadEntry,
} from "./downloads";

const MULTI_DOWNLOAD_DELAY_MS = 400;

type DownloadsDialogProps = {
  transcriptId: string;
  open: boolean;
  onClose: () => void;
};

function showError(message: string) {
  toaster.create({
    duration: 3000,
    render: () => (
      <Box bg="red.500" color="white" px={4} py={3} borderRadius="md">
        <Text fontWeight="bold">Error</Text>
        <Text fontSize="sm">{message}</Text>
      </Box>
    ),
  });
}

function DownloadRow({
  entry,
  checked,
  onToggle,
}: {
  entry: DownloadEntry;
  checked: boolean;
  onToggle: (checked: boolean) => void;
}) {
  const extension = entry.filename.split(".").pop();
  return (
    <Flex align="center" gap={3} py={1}>
      <Checkbox.Root
        checked={checked}
        onCheckedChange={(e) => onToggle(!!e.checked)}
        aria-label={`Select ${entry.label}`}
      >
        <Checkbox.HiddenInput />
        <Checkbox.Control>
          <Checkbox.Indicator />
        </Checkbox.Control>
      </Checkbox.Root>
      <IconButton
        aria-label={`Download ${entry.label}`}
        size="xs"
        variant="ghost"
        onClick={() =>
          startDownload(resolveDownloadUrl(entry.url, API_URL), entry.filename)
        }
      >
        <LuDownload />
      </IconButton>
      <Text flex="1">{entry.label}</Text>
      <Text color="gray.500" fontSize="sm" width="12">
        .{extension}
      </Text>
      <Text color="gray.500" fontSize="sm" width="16" textAlign="right">
        {formatSize(entry.size)}
      </Text>
    </Flex>
  );
}

export default function DownloadsDialog({
  transcriptId,
  open,
  onClose,
}: DownloadsDialogProps) {
  const auth = useAuth();
  const downloads = useTranscriptDownloads(
    parseMaybeNonEmptyString(transcriptId),
    open,
  );
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!open) setSelected(new Set());
  }, [open]);

  useEffect(() => {
    if (downloads.isError) showError("Failed to load the downloads");
  }, [downloads.isError]);

  const entries = downloads.data?.entries ?? [];
  const groups = groupDownloads(entries);
  const selectedEntries = entries.filter((e) => selected.has(e.id));

  const toggle = (id: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  };

  const downloadSelected = () => {
    selectedEntries.forEach((entry, index) => {
      setTimeout(
        () =>
          startDownload(resolveDownloadUrl(entry.url, API_URL), entry.filename),
        index * MULTI_DOWNLOAD_DELAY_MS,
      );
    });
  };

  const downloadZip = () => {
    if (!downloads.data) return;
    startDownload(
      buildZipUrl(
        downloads.data.zip_url,
        selectedEntries.map((e) => e.id),
        API_URL,
      ),
    );
  };

  const renderRows = (items: DownloadEntry[]) =>
    items.map((entry) => (
      <DownloadRow
        key={entry.id}
        entry={entry}
        checked={selected.has(entry.id)}
        onToggle={(checked) => toggle(entry.id, checked)}
      />
    ));

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(e) => {
        if (!e.open) onClose();
      }}
      size="lg"
    >
      <Dialog.Backdrop />
      <Dialog.Positioner>
        <Dialog.Content>
          <Dialog.Header>
            <Dialog.Title>Downloads</Dialog.Title>
            <Dialog.CloseTrigger asChild>
              <CloseButton />
            </Dialog.CloseTrigger>
          </Dialog.Header>
          <Dialog.Body>
            {downloads.isLoading && (
              <Flex justify="center" py={6}>
                <Spinner />
              </Flex>
            )}
            {downloads.isError && (
              <Text color="red.500">Failed to load the downloads.</Text>
            )}
            {downloads.data && (
              <Stack gap={4}>
                {groups.transcript.length > 0 && (
                  <Box>
                    <Text fontWeight="bold" mb={1}>
                      Transcript
                    </Text>
                    {renderRows(groups.transcript)}
                  </Box>
                )}
                {groups.recording.length > 0 && (
                  <Box>
                    <Text fontWeight="bold" mb={1}>
                      Recording
                    </Text>
                    {renderRows(groups.recording)}
                  </Box>
                )}
                {groups.participants.length > 0 && (
                  <Box>
                    <Text fontWeight="bold" mb={1}>
                      Raw streams
                    </Text>
                    {groups.participants.map((participant) => (
                      <Box key={participant.name} mb={2}>
                        <Text fontSize="sm" color="gray.600">
                          {participant.name}
                        </Text>
                        {renderRows(participant.entries)}
                      </Box>
                    ))}
                  </Box>
                )}
                {auth.status !== "authenticated" && (
                  <Text fontSize="sm" color="gray.500">
                    Log in to see the video and the raw streams.
                  </Text>
                )}
              </Stack>
            )}
          </Dialog.Body>
          <Dialog.Footer>
            <Button
              variant="outline"
              onClick={downloadSelected}
              disabled={selectedEntries.length === 0}
            >
              Download selected ({selectedEntries.length})
            </Button>
            <Button
              colorPalette="blue"
              onClick={downloadZip}
              disabled={selectedEntries.length === 0}
            >
              Download selected as zip
            </Button>
          </Dialog.Footer>
        </Dialog.Content>
      </Dialog.Positioner>
    </Dialog.Root>
  );
}

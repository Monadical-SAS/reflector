"use client";

import {
  Button,
  Checkbox,
  CloseButton,
  Dialog,
  Field,
  Flex,
  Heading,
  Input,
  Select,
  Spinner,
  createListCollection,
  useDisclosure,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import useRoomList from "./useRoomList";
import type { components } from "../../reflector-api";
import {
  useRoomCreate,
  useRoomUpdate,
  useRoomDelete,
  useZulipStreams,
  useZulipTopics,
} from "../../lib/apiHooks";
import { RoomList } from "./_components/RoomList";
import { PaginationPage } from "../browse/_components/Pagination";

type Room = components["schemas"]["Room"];

interface SelectOption {
  label: string;
  value: string;
}

const RESERVED_PATHS = ["browse", "rooms", "transcripts"];

const roomModeOptions: SelectOption[] = [
  { label: "2-4 people", value: "normal" },
  { label: "2-200 people", value: "group" },
];

const recordingTriggerOptions: SelectOption[] = [
  { label: "None", value: "none" },
  { label: "Prompt", value: "prompt" },
  { label: "Automatic", value: "automatic-2nd-participant" },
];

const recordingTypeOptions: SelectOption[] = [
  { label: "None", value: "none" },
  { label: "Local", value: "local" },
  { label: "Cloud", value: "cloud" },
];

const roomInitialState = {
  name: "",
  zulipAutoPost: false,
  zulipStream: "",
  zulipTopic: "",
  isLocked: false,
  roomMode: "normal",
  recordingType: "cloud",
  recordingTrigger: "automatic-2nd-participant",
  isShared: false,
};

export default function RoomsList() {
  const { open, onOpen, onClose } = useDisclosure();

  // Create collections for Select components
  const roomModeCollection = createListCollection({
    items: roomModeOptions,
  });

  const recordingTriggerCollection = createListCollection({
    items: recordingTriggerOptions,
  });

  const recordingTypeCollection = createListCollection({
    items: recordingTypeOptions,
  });
  const [room, setRoom] = useState(roomInitialState);
  const [isEditing, setIsEditing] = useState(false);
  const [editRoomId, setEditRoomId] = useState("");
  // TODO seems to be no setPage calls
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useRoomList(PaginationPage(page));
  const [nameError, setNameError] = useState("");
  const [linkCopied, setLinkCopied] = useState("");
  const [selectedStreamId, setSelectedStreamId] = useState<number | null>(null);

  const createRoomMutation = useRoomCreate();
  const updateRoomMutation = useRoomUpdate();
  const deleteRoomMutation = useRoomDelete();
  const { data: streams = [] } = useZulipStreams() as { data: any[] };
  const { data: topics = [] } = useZulipTopics(selectedStreamId) as {
    data: Topic[];
  };
  interface Topic {
    name: string;
  }

  // Update selected stream ID when zulip stream changes
  useEffect(() => {
    if (room.zulipStream && streams.length > 0) {
      const selectedStream = streams.find(
        (s: any) => s.name === room.zulipStream,
      );
      if (selectedStream) {
        setSelectedStreamId((selectedStream as any).stream_id);
      }
    } else {
      setSelectedStreamId(null);
    }
  }, [room.zulipStream, streams]);

  const streamOptions: SelectOption[] = streams.map((stream: any) => {
    return { label: stream.name, value: stream.name };
  });

  const topicOptions: SelectOption[] = topics.map((topic: any) => ({
    label: topic.name,
    value: topic.name,
  }));

  const streamCollection = createListCollection({
    items: streamOptions,
  });

  const topicCollection = createListCollection({
    items: topicOptions,
  });

  const handleCopyUrl = (roomName: string) => {
    const roomUrl = `${window.location.origin}/${roomName}`;
    navigator.clipboard.writeText(roomUrl);
    setLinkCopied(roomName);

    setTimeout(() => {
      setLinkCopied("");
    }, 2000);
  };

  const handleSaveRoom = async () => {
    try {
      if (RESERVED_PATHS.includes(room.name)) {
        setNameError("This room name is reserved. Please choose another name.");
        return;
      }

      const roomData = {
        name: room.name,
        zulip_auto_post: room.zulipAutoPost,
        zulip_stream: room.zulipStream,
        zulip_topic: room.zulipTopic,
        is_locked: room.isLocked,
        room_mode: room.roomMode,
        recording_type: room.recordingType,
        recording_trigger: room.recordingTrigger,
        is_shared: room.isShared,
      };

      if (isEditing) {
        await updateRoomMutation.mutateAsync({
          params: {
            path: { room_id: editRoomId },
          },
          body: roomData,
        });
      } else {
        await createRoomMutation.mutateAsync({
          body: roomData,
        });
      }

      setRoom(roomInitialState);
      setIsEditing(false);
      setEditRoomId("");
      setNameError("");
      refetch();
      onClose();
    } catch (err: any) {
      if (
        err?.status === 400 &&
        err?.body?.detail == "Room name is not unique"
      ) {
        setNameError(
          "This room name is already taken. Please choose a different name.",
        );
      } else {
        setNameError("An error occurred. Please try again.");
      }
    }
  };

  const handleEditRoom = (roomId, roomData) => {
    setRoom({
      name: roomData.name,
      zulipAutoPost: roomData.zulip_auto_post,
      zulipStream: roomData.zulip_stream,
      zulipTopic: roomData.zulip_topic,
      isLocked: roomData.is_locked,
      roomMode: roomData.room_mode,
      recordingType: roomData.recording_type,
      recordingTrigger: roomData.recording_trigger,
      isShared: roomData.is_shared,
    });
    setEditRoomId(roomId);
    setIsEditing(true);
    setNameError("");
    onOpen();
  };

  const handleDeleteRoom = async (roomId: string) => {
    try {
      await deleteRoomMutation.mutateAsync({
        params: {
          path: { room_id: roomId },
        },
      });
      refetch();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRoomChange = (e) => {
    let { name, value, type, checked } = e.target;
    if (name === "name") {
      value = value
        .replace(/[^a-zA-Z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .toLowerCase();
      setNameError("");
    }
    setRoom({
      ...room,
      [name]: type === "checkbox" ? checked : value,
    });
  };

  const myRooms: Room[] =
    response?.items.filter((roomData) => !roomData.is_shared) || [];
  const sharedRooms: Room[] =
    response?.items.filter((roomData) => roomData.is_shared) || [];

  if (loading && !response)
    return (
      <Flex
        flexDir="column"
        alignItems="center"
        justifyContent="center"
        h="100%"
      >
        <Spinner size="xl" />
      </Flex>
    );

  return (
    <Flex
      flexDir="column"
      w={{ base: "full", md: "container.xl" }}
      mx="auto"
      pt={2}
    >
      <Flex
        flexDir="row"
        justifyContent="space-between"
        alignItems="center"
        mb={4}
      >
        <Heading size="lg">Rooms {loading && <Spinner size="sm" />}</Heading>
        <Button
          colorPalette="primary"
          onClick={() => {
            setIsEditing(false);
            setRoom(roomInitialState);
            setNameError("");
            onOpen();
          }}
        >
          Add Room
        </Button>
      </Flex>

      <Dialog.Root
        open={open}
        onOpenChange={(e) => (e.open ? onOpen() : onClose())}
        size="lg"
      >
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content>
            <Dialog.Header>
              <Dialog.Title>
                {isEditing ? "Edit Room" : "Add Room"}
              </Dialog.Title>
              <Dialog.CloseTrigger asChild>
                <CloseButton />
              </Dialog.CloseTrigger>
            </Dialog.Header>
            <Dialog.Body>
              <Field.Root>
                <Field.Label>Room name</Field.Label>
                <Input
                  name="name"
                  placeholder="room-name"
                  value={room.name}
                  onChange={handleRoomChange}
                />
                <Field.HelperText>
                  No spaces or special characters allowed
                </Field.HelperText>
                {nameError && <Field.ErrorText>{nameError}</Field.ErrorText>}
              </Field.Root>

              <Field.Root mt={4}>
                <Checkbox.Root
                  name="isLocked"
                  checked={room.isLocked}
                  onCheckedChange={(e) => {
                    const syntheticEvent = {
                      target: {
                        name: "isLocked",
                        type: "checkbox",
                        checked: e.checked,
                      },
                    };
                    handleRoomChange(syntheticEvent);
                  }}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control>
                    <Checkbox.Indicator />
                  </Checkbox.Control>
                  <Checkbox.Label>Locked room</Checkbox.Label>
                </Checkbox.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Field.Label>Room size</Field.Label>
                <Select.Root
                  value={[room.roomMode]}
                  onValueChange={(e) =>
                    setRoom({ ...room, roomMode: e.value[0] })
                  }
                  collection={roomModeCollection}
                >
                  <Select.HiddenSelect />
                  <Select.Control>
                    <Select.Trigger>
                      <Select.ValueText placeholder="Select room size" />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Select.Positioner>
                    <Select.Content>
                      {roomModeOptions.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Select.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Field.Label>Recording type</Field.Label>
                <Select.Root
                  value={[room.recordingType]}
                  onValueChange={(e) =>
                    setRoom({
                      ...room,
                      recordingType: e.value[0],
                      recordingTrigger:
                        e.value[0] !== "cloud" ? "none" : room.recordingTrigger,
                    })
                  }
                  collection={recordingTypeCollection}
                >
                  <Select.HiddenSelect />
                  <Select.Control>
                    <Select.Trigger>
                      <Select.ValueText placeholder="Select recording type" />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Select.Positioner>
                    <Select.Content>
                      {recordingTypeOptions.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Select.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Field.Label>Cloud recording start trigger</Field.Label>
                <Select.Root
                  value={[room.recordingTrigger]}
                  onValueChange={(e) =>
                    setRoom({ ...room, recordingTrigger: e.value[0] })
                  }
                  collection={recordingTriggerCollection}
                  disabled={room.recordingType !== "cloud"}
                >
                  <Select.HiddenSelect />
                  <Select.Control>
                    <Select.Trigger>
                      <Select.ValueText placeholder="Select trigger" />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Select.Positioner>
                    <Select.Content>
                      {recordingTriggerOptions.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Select.Root>
              </Field.Root>
              <Field.Root mt={8}>
                <Checkbox.Root
                  name="zulipAutoPost"
                  checked={room.zulipAutoPost}
                  onCheckedChange={(e) => {
                    const syntheticEvent = {
                      target: {
                        name: "zulipAutoPost",
                        type: "checkbox",
                        checked: e.checked,
                      },
                    };
                    handleRoomChange(syntheticEvent);
                  }}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control>
                    <Checkbox.Indicator />
                  </Checkbox.Control>
                  <Checkbox.Label>
                    Automatically post transcription to Zulip
                  </Checkbox.Label>
                </Checkbox.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Field.Label>Zulip stream</Field.Label>
                <Select.Root
                  value={room.zulipStream ? [room.zulipStream] : []}
                  onValueChange={(e) =>
                    setRoom({
                      ...room,
                      zulipStream: e.value[0],
                      zulipTopic: "",
                    })
                  }
                  collection={streamCollection}
                  disabled={!room.zulipAutoPost}
                >
                  <Select.HiddenSelect />
                  <Select.Control>
                    <Select.Trigger>
                      <Select.ValueText placeholder="Select stream" />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Select.Positioner>
                    <Select.Content>
                      {streamOptions.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Select.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Field.Label>Zulip topic</Field.Label>
                <Select.Root
                  value={room.zulipTopic ? [room.zulipTopic] : []}
                  onValueChange={(e) =>
                    setRoom({ ...room, zulipTopic: e.value[0] })
                  }
                  collection={topicCollection}
                  disabled={!room.zulipAutoPost}
                >
                  <Select.HiddenSelect />
                  <Select.Control>
                    <Select.Trigger>
                      <Select.ValueText placeholder="Select topic" />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Select.Positioner>
                    <Select.Content>
                      {topicOptions.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Select.Root>
              </Field.Root>
              <Field.Root mt={4}>
                <Checkbox.Root
                  name="isShared"
                  checked={room.isShared}
                  onCheckedChange={(e) => {
                    const syntheticEvent = {
                      target: {
                        name: "isShared",
                        type: "checkbox",
                        checked: e.checked,
                      },
                    };
                    handleRoomChange(syntheticEvent);
                  }}
                >
                  <Checkbox.HiddenInput />
                  <Checkbox.Control>
                    <Checkbox.Indicator />
                  </Checkbox.Control>
                  <Checkbox.Label>Shared room</Checkbox.Label>
                </Checkbox.Root>
              </Field.Root>
            </Dialog.Body>
            <Dialog.Footer>
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
              <Button
                colorPalette="primary"
                onClick={handleSaveRoom}
                disabled={
                  !room.name || (room.zulipAutoPost && !room.zulipTopic)
                }
              >
                {isEditing ? "Save" : "Add"}
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Dialog.Root>

      <RoomList
        title="My Rooms"
        rooms={myRooms}
        linkCopied={linkCopied}
        onCopyUrl={handleCopyUrl}
        onEdit={handleEditRoom}
        onDelete={handleDeleteRoom}
        emptyMessage="No rooms found"
      />

      <RoomList
        title="Shared Rooms"
        rooms={sharedRooms}
        linkCopied={linkCopied}
        onCopyUrl={handleCopyUrl}
        onEdit={handleEditRoom}
        onDelete={handleDeleteRoom}
        emptyMessage="No shared rooms found"
        pt={4}
      />
    </Flex>
  );
}

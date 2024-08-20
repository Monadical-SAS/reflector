"use client";

import {
  Box,
  Button,
  Card,
  CardBody,
  Flex,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  Heading,
  Input,
  Link,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Spacer,
  Spinner,
  useDisclosure,
  VStack,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  AlertDialog,
  IconButton,
} from "@chakra-ui/react";
import NextLink from "next";
import React, { ReactNode, useState } from "react";
import { Container } from "@chakra-ui/react";
import { PlusSquareIcon } from "@chakra-ui/icons";
import useApi from "../../lib/useApi";
import useRoomList from "./useRoomList";
import { FaEllipsisVertical, FaTrash } from "react-icons/fa6";
import next from "next";

export default function RoomsList() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [roomName, setRoomName] = useState("");
  const api = useApi();
  const [page, setPage] = useState<number>(1);
  const { loading, response, refetch } = useRoomList(page);

  const handleAddRoom = async () => {
    try {
      const response = await api?.v1RoomsCreate({
        requestBody: { name: roomName },
      });
      setRoomName("");
      refetch();
    } catch (err) {}
    onClose();
  };

  const handleDeleteRoom = async (roomId: string) => {
    try {
      const response = await api?.v1RoomsDelete({
        roomId,
      });
      refetch();
    } catch (err) {}
  };

  const handleRoomNameChange = (e) => {
    setRoomName(e.target.value);
  };

  if (loading && !response)
    return (
      <Flex flexDir="column" align="center" justify="center" h="100%">
        <Spinner size="xl" />
      </Flex>
    );

  return (
    <>
      <Container maxW={"container.lg"}>
        <Flex
          flexDir="row"
          justify="flex-end"
          align="center"
          flexWrap={"wrap-reverse"}
          mb={2}
        >
          <Heading>Rooms</Heading>
          <Spacer />
          <Button colorScheme="blue" onClick={onOpen}>
            Add Room
          </Button>
          <Modal isOpen={isOpen} onClose={onClose}>
            <ModalOverlay />
            <ModalContent>
              <ModalHeader>Add Room</ModalHeader>
              <ModalCloseButton />
              <ModalBody>
                <FormControl>
                  <FormLabel>Room name</FormLabel>
                  <Input
                    placeholder="room-name"
                    value={roomName}
                    onChange={handleRoomNameChange}
                  />
                  <FormHelperText>Please enter room name</FormHelperText>
                </FormControl>
              </ModalBody>

              <ModalFooter>
                <Button variant="ghost" mr={3} onClick={onClose}>
                  Cancel
                </Button>

                <Button colorScheme="blue" onClick={handleAddRoom}>
                  Add
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </Flex>

        <VStack>
          {response?.items && response.items.length > 0 ? (
            response.items.map((room) => (
              <Card w={"full"}>
                <CardBody>
                  <Flex align={"center"}>
                    <Heading size="md">
                      <Link
                        // as={NextLink}
                        href={`/rooms/${room.name}`}
                        noOfLines={2}
                      >
                        {room.name}
                      </Link>
                    </Heading>
                    <Spacer />
                    <Menu closeOnSelect={true}>
                      <MenuButton
                        as={IconButton}
                        icon={<FaEllipsisVertical />}
                        aria-label="actions"
                      />
                      <MenuList>
                        <MenuItem
                          onClick={() => handleDeleteRoom(room.id)}
                          icon={<FaTrash color={"red.500"} />}
                        >
                          Delete
                        </MenuItem>
                      </MenuList>
                    </Menu>
                  </Flex>
                </CardBody>
              </Card>
            ))
          ) : (
            <Flex flexDir="column" align="center" justify="center" h="100%">
              <Text>No rooms found</Text>
            </Flex>
          )}
        </VStack>
      </Container>
    </>
  );
}

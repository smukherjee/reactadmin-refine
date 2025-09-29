import React from "react";
import {
  List,
  TextField,
  EmailField,
  BooleanField,
  DateField,
  useTable,
  EditButton,
  ShowButton,
  DeleteButton,
} from "@refinedev/mui";
import { Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

export const UserList = () => {
  const { tableQueryResult } = useTable({
    resource: "users",
  });

  const { data, isLoading } = tableQueryResult;

  return (
    <List>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>First Name</TableCell>
            <TableCell>Last Name</TableCell>
            <TableCell>Active</TableCell>
            <TableCell>Created At</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data?.data?.map((user) => (
            <TableRow key={user.id}>
              <TableCell>
                <TextField value={user.id} />
              </TableCell>
              <TableCell>
                <EmailField value={user.email} />
              </TableCell>
              <TableCell>
                <TextField value={user.first_name} />
              </TableCell>
              <TableCell>
                <TextField value={user.last_name} />
              </TableCell>
              <TableCell>
                <BooleanField value={user.is_active} />
              </TableCell>
              <TableCell>
                <DateField value={user.created_at} />
              </TableCell>
              <TableCell>
                <EditButton hideText recordItemId={user.id} />
                <ShowButton hideText recordItemId={user.id} />
                <DeleteButton hideText recordItemId={user.id} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </List>
  );
};
"""CLI for MiniCon."""

import os
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from src.container.manager import ContainerManager
from src.container.model import State


class MiniConCLI:
    """MiniCon CLI for container management.

    This class provides a command-line interface for the MiniCon container system.
    It offers commands to create, list, start, stop, remove, and run containers.
    The CLI is built using Typer and Rich for improved user experience.

    Attributes:
        app (typer.Typer): The Typer application instance for command registration.
        console (Console): Rich console for formatted output.
    """

    def __init__(self) -> None:
        """Initialize the CLI with common resources."""
        self.app = typer.Typer(help="MiniCon: A lightweight container implementation")
        self.console = Console()

        self.app.command("create")(self.create)
        self.app.command("list")(self.list)
        self.app.command("start")(self.start)
        self.app.command("stop")(self.stop)
        self.app.command("rm")(self.remove)
        self.app.command("run")(self.run)

    def _check_root(self) -> None:
        if os.geteuid() != 0:
            message = "[bold red]Error:[/] This command requires root privileges"
            self.console.print(message)
            raise typer.Exit(1)

    def create(
        self,
        name: str = typer.Option(..., "--name", "-n", help="Container name"),
        command: List[str] = typer.Argument(
            ..., help="Command to run in the container"
        ),
    ) -> None:
        """Create a new container with the specified name and command.

        This command creates a new container with the given name and command.
        It returns the container ID that can be used to reference the container
        in other commands. The container is created in the 'created' state and
        needs to be started separately with the 'start' command.

        Args:
            name: The name to assign to the container for easier identification.
            command: The command and its arguments to run inside the container.
        """
        self._check_root()

        manager = ContainerManager()
        container_id = manager.create(name, command)
        self.console.print(f"Container created with ID: [bold green]{container_id}[/]")

    def list(
        self,
        state: Optional[str] = typer.Option(
            None,
            "--state",
            "-s",
            help="Filter by container state (created, running, exited)",
        ),
    ) -> None:
        """List all containers, optionally filtered by state.

        This command displays a table of containers with their ID, name, state,
        process ID (if running), and command. The output can be filtered to show
        only containers in a specific state (created, running, or exited).

        Args:
            state: Optional state filter to show only containers in the specified state.
                  Valid values are "created", "running", or "exited".
        """
        manager = ContainerManager()

        filter_state = None
        if state:
            try:
                filter_state = State(state)
            except ValueError:
                self.console.print(f"[bold red]Error:[/] Invalid state: {state}")
                raise typer.Exit(1)

        containers = manager.list(filter_state)

        if not containers:
            self.console.print("No containers found")
            return

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("NAME")
        table.add_column("STATE", style="green")
        table.add_column("PID")
        table.add_column("COMMAND")

        for container in containers:
            pid = str(container.process_id) if container.process_id else "-"
            cmd = " ".join(container.command[:3]) + (
                "..." if len(container.command) > 3 else ""
            )
            state_style = {
                "created": "blue",
                "running": "green",
                "exited": "red",
            }.get(container.state.value, "")

            table.add_row(
                container.id,
                container.name,
                f"[{state_style}]{container.state.value}[/{state_style}]",
                pid,
                cmd,
            )

        self.console.print(table)

    def start(
        self,
        container_id: str = typer.Argument(..., help="Container ID to start"),
    ) -> None:
        """Start a container.

        This command starts a container with the specified ID. The container must be
        in the 'created' state. Once started, the container will transition to the
        'running' state and execute the command specified during creation.

        Args:
            container_id: The unique identifier of the container to start.

        Raises:
            typer.Exit: If the container cannot be started due to an error.
        """
        self._check_root()

        with self.console.status(f"Starting container {container_id}..."):
            manager = ContainerManager()
            try:
                manager.start(container_id)
                self.console.print(
                    f"Container [bold]{container_id}[/] started successfully"
                )
            except ValueError as e:
                self.console.print(f"[bold red]Error:[/] {str(e)}")
                raise typer.Exit(1)
            except Exception as e:
                self.console.print(
                    f"[bold red]Error:[/] Failed to start container: {str(e)}"
                )
                raise typer.Exit(1)

    def stop(
        self,
        container_id: str = typer.Argument(..., help="Container ID to stop"),
    ) -> None:
        """Stop a running container.

        This command stops a container with the specified ID. The container must be
        in the 'running' state. Once stopped, the container will transition to the
        'exited' state. This command sends a signal to the container's main process
        and waits for it to exit gracefully.

        Args:
            container_id: The unique identifier of the container to stop.

        Raises:
            typer.Exit: If the container cannot be stopped due to an error.
        """
        self._check_root()

        with self.console.status(f"Stopping container {container_id}..."):
            manager = ContainerManager()
            try:
                manager.stop(container_id)
                self.console.print(
                    f"Container [bold]{container_id}[/] stopped successfully"
                )
            except ValueError as e:
                self.console.print(f"[bold red]Error:[/] {str(e)}")
                raise typer.Exit(1)
            except Exception as e:
                self.console.print(
                    f"[bold red]Error:[/] Failed to stop container: {str(e)}"
                )
                raise typer.Exit(1)

    def remove(
        self,
        container_id: str = typer.Argument(..., help="Container ID to remove"),
    ) -> None:
        """Remove a container.

        This command removes a container with the specified ID.
        The container must not be in the 'running' state.
        This operation permanently deletes the container and its
        associated resources from the system. Once removed, the container cannot be
        recovered.

        Args:
            container_id: The unique identifier of the container to remove.

        Raises:
            typer.Exit: If the container cannot be removed due to an error, such as
                if it is still running or does not exist.
        """
        self._check_root()

        manager = ContainerManager()
        try:
            manager.remove(container_id)
            self.console.print(
                f"Container [bold]{container_id}[/] removed successfully"
            )
        except ValueError as e:
            self.console.print(f"[bold red]Error:[/] {str(e)}")
            raise typer.Exit(1)

    def run(
        self,
        name: str = typer.Option(..., "--name", "-n", help="Container name"),
        command: List[str] = typer.Argument(
            ..., help="Command to run in the container"
        ),
        memory: int = typer.Option(
            250 * 1024 * 1024,
            "--memory",
            "-m",
            help="Memory limit in bytes (default: 250MB)",
        ),
    ) -> None:
        """Run a container with the specified name, command, and memory limit.

        This command creates and starts a new container with the given name and command.
        It allocates the specified amount of memory to the container and runs the
        command inside the container's isolated environment.

        Args:
            name: A human-readable name for the container.
            command: The command and its arguments to run inside the container.
            memory: Memory limit in bytes for the container. Defaults to 250MB.

        Raises:
            typer.Exit: If the container cannot be created or started due to an error,
                such as insufficient resources or invalid configuration.
        """
        self._check_root()

        manager = ContainerManager()

        # Create the container
        with self.console.status(f"Creating container {name}..."):
            container_id = manager.create(name, command, memory)

        # Start the container
        with self.console.status(f"Starting container {container_id}..."):
            try:
                manager.start(container_id)
                self.console.print(
                    f"Container [bold green]{container_id}[/] started successfully"
                )
            except Exception as e:
                self.console.print(
                    f"[bold red]Error:[/] Failed to start container: {str(e)}"
                )
                raise typer.Exit(1)


def main() -> None:
    """Entry point for the MiniCon CLI application.

    This function initializes and runs the MiniCon command-line interface.
    It sets up the CLI application, processes command-line arguments,
    and executes the appropriate commands based on user input.

    The CLI provides functionality for container management operations such as:
    - Creating containers
    - Starting containers
    - Stopping containers
    - Removing containers
    - Listing containers

    Returns:
        None
    """
    cli = MiniConCLI()
    cli.app()


if __name__ == "__main__":
    main()

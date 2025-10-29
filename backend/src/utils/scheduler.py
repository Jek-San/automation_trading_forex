# src/utils/scheduler.py

class Scheduler:
    def __init__(self):
        self.services = {}

    def register(self, service):
        self.services[service.name] = service
        print(f"🧩 Registered service: {service.name}")

    async def start_all(self):
        for service in self.services.values():
            await service.start()

    async def stop_all(self):
        for service in self.services.values():
            await service.stop()

    def get_status(self):
        """Return all services with their current status (for UI)"""
        return [
            {
                "name": name,
                "description": getattr(service, "description", ""),
                "status": "running" if service.running else "stopped",
            }
            for name, service in self.services.items()
        ]

    async def start_service(self, name: str):
        """Start a single service by name"""
        service = self.services.get(name)
        if service and not service.running:
            await service.start()
            print(f"▶️ Started service: {name}")
            return True
        return False

    async def stop_service(self, name: str):
        """Stop a single service by name"""
        service = self.services.get(name)
        if service and service.running:
            await service.stop()
            print(f"⏹️ Stopped service: {name}")
            return True
        return False
